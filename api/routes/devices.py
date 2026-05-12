import logging

from flask import Blueprint, jsonify, request

from database import get_conn
from schemas import Device

logger = logging.getLogger(__name__)
devices_bp = Blueprint("devices", __name__)

@devices_bp.route("/registerDevice", methods=["POST"])
def register_device():
    try:
        payload = Device.model_validate(request.json)
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Check if MAC address already registered
                cur.execute("""
                    SELECT device_id 
                    FROM Devices 
                    WHERE mac_address = %s
                    """, (payload.mac_address,))
                row = cur.fetchone()

                if row:
                    logger.info(f"Re-registered device {row['device_id']}.")
                    return jsonify({"uuid": str(row["device_id"]) }), 201

                # If not, Register device into database
                cur.execute("""
                INSERT INTO Devices (mac_address)
                VALUES (%s)
                RETURNING device_id
                """, (payload.mac_address,))
                new_uuid = cur.fetchone()["device_id"]

                cur.execute("""
                    SELECT sensor_type, trigger_value, trigger_when_below, alert_message
                    FROM Default_Thresholds
                    """)
                # add default thresholds
                defaults = cur.fetchall()
                for t in defaults:
                    cur.execute("""
                        INSERT INTO Alert_Thresholds
                        (device_id,trigger_value,sensor_type,trigger_when_below,alert_message)
                        VALUES (%s, %s, %s, %s, %s);
                        """, (
                        new_uuid,
                        t["trigger_value"],
                        t["sensor_type"],
                        t["trigger_when_below"],
                        t["alert_message"]))

                logger.info(f"Added new device {new_uuid}.")        
                return jsonify({"uuid": str(new_uuid)}), 201

    except Exception as e:
        logger.error(f"Failure registering device: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route("/devices", methods=["GET"])
def get_devices():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * 
                    FROM Devices 
                    ORDER BY serial_number
                    """)
                devices = cur.fetchall()
                return jsonify(devices), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@devices_bp.route("/devices/<device_id>", methods=["PUT"])
def update_device(device_id):
    data = request.json
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE Devices
                    SET device_name = %s, height_buffer = %s, 
                        bin_height = %s, alerts_enabled = %s
                    WHERE device_id = %s
                    """, (data["device_name"], data["height_buffer"], 
                    data["bin_height"], data["alerts_enabled"], device_id))
            conn.commit()
            return jsonify({"message": "Updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- GET RECIPIENTS FOR A DEVICE ---
@devices_bp.route("/devices/<device_id>/recipients", methods=["GET"])
def get_device_recipients(device_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT contact_id FROM Alert_Recipients WHERE device_id = %s",
                    (device_id,)
                )
                recipients = [row["contact_id"] for row in cur.fetchall()]
                return jsonify(recipients), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@devices_bp.route("/devices/<device_id>/recipients", methods=["POST"])
def sync_device_recipients(device_id):
    data = request.json  # Expects a list of contact_ids: [1, 2, 3]
    new_contact_ids = data.get("contact_ids", [])
    
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 1. Clear existing links for this device
                cur.execute("DELETE FROM Alert_Recipients WHERE device_id = %s", (device_id,))
                
                # 2. Insert new links
                for uid in new_contact_ids:
                    cur.execute(
                        "INSERT INTO Alert_Recipients (device_id, contact_id) VALUES (%s, %s)",
                        (device_id, uid)
                    )
            conn.commit()
            return jsonify({"message": "Recipients updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500