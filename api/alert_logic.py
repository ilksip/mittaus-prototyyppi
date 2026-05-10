import logging

from mail_sender import send_email

logger = logging.getLogger(__name__)

def fetch_device_settings(cur, device_id):
    cur.execute("""
        SELECT device_name, bin_height, height_buffer, alerts_enabled
        FROM Devices
        WHERE device_id = %s;
        """, (device_id,))
    return cur.fetchone()
def is_duplicate_alert(cur, device_id, sensor_type, threshold_value):
    cur.execute("""
        SELECT * FROM Alert_History 
        WHERE device_id = %s
        AND sensor_type = %s
        AND threshold_value = %s
        AND created_at >= NOW() - INTERVAL '24 hours'
        LIMIT 1;
        """, (device_id, sensor_type, threshold_value))
    return cur.fetchone()
def get_device_thresholds(cur, device_id):
    cur.execute("""
        SELECT threshold_id, sensor_type, trigger_value, trigger_when_below, alert_message
        FROM Alert_Thresholds
        WHERE device_id = %s;
        """, (device_id,))  # noqa: E501
    return cur.fetchall()
def get_triggered_threshold(relevant_thresholds, current_value):
    triggered = [
        t for t in relevant_thresholds
        if (current_value < t["trigger_value"] if t["trigger_when_below"]
            else current_value > t["trigger_value"])]
    if not triggered:
        return None

    if relevant_thresholds[0]["trigger_when_below"]:
        return min(triggered, key=lambda t: t["trigger_value"])
    else:
        return max(triggered, key=lambda t: t["trigger_value"])
def get_email_addresses(cur, device_id):
    cur.execute("""
        SELECT u.email 
        FROM Alert_Recipients ar JOIN Users u 
        ON ar.user_id = u.user_id 
        WHERE ar.device_id = %s;
        """, (device_id,))
    return [row["email"] for row in cur.fetchall()]

def handle_alert_logic(device_id: str, sensor_values: dict, created_at, conn):
    logger.debug("Alert system!")
    with conn.cursor() as cur:
        # Get device-specific values.
        device = fetch_device_settings(cur, device_id)
        # Return if no device exists, or alerts are disabled for device
        if not device or not device["alerts_enabled"]:
            logger.info(f"Alerts disabled or device {device_id} not found.")
            return
        logger.debug("Get thrasholds:")
        # Get thresholds for this device
        thresholds = get_device_thresholds(cur, device_id)

        # Check if any thresholds are triggered
        for sensor_type, value in sensor_values.items():
            # Value is -1 if sensor fails, so it is skipped
            if (value == -1): 
                continue
            logger.debug(f"Checking thresholds for {sensor_type}: {value}")        
            relevant = [t for t in thresholds if t["sensor_type"] == sensor_type]
            if not relevant:
                continue
            
            check_value = value

            
            if sensor_type == "fill_level":
                logger.debug("Fill level")  
                # alter fill level from sensor value into percentage if fill_level
                real_measurement = value - device["height_buffer"]
                fill_percentage = ((device["bin_height"] - (real_measurement)) / device["bin_height"]) * 100  # noqa: E501
                check_value = min(fill_percentage, 100)

                logger.debug(
                    f"Space left: {round(real_measurement, 2)}cm out of {device['bin_height']}cm\n" # noqa: E501
                    f"Fill level: {check_value:.2f}%")
            
            selected = get_triggered_threshold(relevant, check_value)

            if not selected:
                logger.debug("No thresholds triggered!")
                continue
            logger.debug(f"Triggered: {selected['sensor_type']}: {selected['trigger_value']}")  # noqa: E501

            # Deduplication (no mail if already sent in 24h)
            if is_duplicate_alert(cur, device_id, sensor_type, selected["trigger_value"]): # noqa: E501
                logger.debug("An alert has already been sent in past 24 hours! Skipping...")  # noqa: E501
                continue        
            # Get all e-mails to send to
            emails = get_email_addresses(cur, device_id)
            
            if not emails:
                logger.error("Couldn't send email! No contacts defined for device!")
                continue

            logger.debug(f"{emails}")
            # Send alerts
            for address in emails:
                send_email(
                    address, device_id, device["device_name"],
                    sensor_type, selected["trigger_value"], check_value,
                    created_at, selected["alert_message"])