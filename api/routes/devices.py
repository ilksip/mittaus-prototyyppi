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
                cur.execute("SELECT device_id FROM Devices WHERE mac_address = %s", (payload.mac_address,))
                row = cur.fetchone()

                if row:
                    logger.info(f"Re-registered device {row['device_id']}.")
                    return jsonify({"uuid": str(row["device_id"]) }), 201

                # If not, Register device into database
                cur.execute("""INSERT INTO Devices (mac_address) VALUES (%s) RETURNING device_id""", (payload.mac_address,))
                new_uuid = cur.fetchone()["device_id"]

                cur.execute("SELECT sensor_type, trigger_value, trigger_when_below, alert_message FROM Default_Thresholds")
                # add default thresholds
                defaults = cur.fetchall()
                for t in defaults:
                    cur.execute("""INSERT INTO Alert_Thresholds
                        (device_id,trigger_value,sensor_type,trigger_when_below,alert_message)
                        VALUES (%s, %s, %s, %s, %s);""",
                        (new_uuid,t["trigger_value"],t["sensor_type"],t["trigger_when_below"],t["alert_message"]))

                logger.info(f"Added new device {new_uuid}.")        
                return jsonify({"uuid": str(new_uuid)}), 201

    except Exception as e:
        logger.error(f"Failure registering device: {e}")
        return jsonify({"error": str(e)}), 500

@devices_bp.route("/devices", methods=["GET"])
def list_devices():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM Devices ORDER BY serial_number")
                devices = cur.fetchall()
                return jsonify(devices), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500