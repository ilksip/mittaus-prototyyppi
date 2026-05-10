import logging

from config import format_timestamp
from mail_sender import send_email

logger = logging.getLogger(__name__)

def handle_alert_logic(device_id: str, sensor_values: dict, created_at, conn):

    with conn.cursor() as cur:
    # Get bin height for calculations (and name for email)
        cur.execute("""
            SELECT device_name, bin_height, height_buffer, alerts_enabled
            FROM Devices
            WHERE device_id = %s;
            """, (device_id,))
        device = cur.fetchone()
        
        device_name = device["device_name"]
        bin_height = device["bin_height"]
        height_buffer = device["height_buffer"]
        alerts_enabled = device["alerts_enabled"]
    # Get thresholds for this device
        cur.execute("""
            SELECT threshold_id, sensor_type, trigger_value, trigger_when_below,
            alert_message 
            FROM Alert_Thresholds
            WHERE device_id = %s;
            """, (device_id,))
        thresholds = cur.fetchall()

    # Check if any thresholds are triggered
        for sensor_type, value in sensor_values.items():

            relevant = [t for t in thresholds if t["sensor_type"] == sensor_type]
            if not relevant:
                continue

            check_value = value
            if (check_value == -1): 
                continue #

            # alter fill level from sensor value into percentage if fill_level
            if sensor_type == "fill_level":
                check_value = min(((bin_height - (value - height_buffer)) / bin_height) * 100, 100) # noqa: E501
                logger.debug(   f"Converted fill_level distance {value - height_buffer} using bin_height {bin_height} " # noqa: E501
                                f"to fill percentage {check_value:.2f}%")
            triggered = [
                t for t in relevant
                if (check_value < t["trigger_value"] if t["trigger_when_below"]
                    else check_value > t["trigger_value"])]
            if not triggered:
                continue
        
        # Select most severe threshold from those triggered
            if relevant[0]["trigger_when_below"]:
                selected = min(triggered, key=lambda t: t["trigger_value"])
            else:
                selected = max(triggered, key=lambda t: t["trigger_value"])

            logger.debug(f"Triggered: {selected['sensor_type']}: {selected['trigger_value']}") # noqa: E501
            if alerts_enabled:
        # Deduplication (no mail if already sent in 24h)
                cur.execute("""
                    SELECT * FROM Alert_History 
                    WHERE device_id = %s
                    AND sensor_type = %s
                    AND threshold_value = %s
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    LIMIT 1;
                    """, (device_id, sensor_type, selected["trigger_value"]))
                result = cur.fetchone()
                if result:
                    logger.info("Found alert in past 24 hours! Skipping sending alert!")
                    logger.debug(f"Alert id: {result['alert_id']} at {format_timestamp(result['created_at'])}")  # noqa: E501
                    continue
        # Get all e-mails to send to
                cur.execute("""
                    SELECT u.email 
                    FROM Alert_Recipients ar JOIN Users u 
                    ON ar.user_id = u.user_id 
                    WHERE ar.device_id = %s;
                    """, (device_id,))
                emails = [row["email"] for row in cur.fetchall()]
                logger.debug(f"{emails}")
                if not emails:
                    logger.error("Couldn't send email! No contacts defined for device!")
                    continue
                
        # Send alerts
                for address in emails:
                    send_email(
                        address,
                        device_id,
                        device_name,
                        sensor_type,
                        selected["trigger_value"],
                        check_value,
                        created_at,
                        selected["alert_message"]
                    )
            else:
                logger.info("Alerts disabled for this device.")