from flask import Flask, request, jsonify
import psycopg
from psycopg.types.json import Json
from psycopg.rows import dict_row
from pydantic import ValidationError
from schemas import Telemetry, Device

import os, uuid, json, logging
from database import get_conn, INSERT_DEFAULT_ALERT_THRESHOLDS
from alert_logic import handle_alert_logic
from config import setup_app_logging
setup_app_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/api/registerDevice", methods=["POST"])
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
                cur.execute("INSERT INTO Devices (mac_address) VALUES (%s) RETURNING device_id", (payload.mac_address,))
                new_uuid = cur.fetchone()["device_id"]

                cur.execute("SELECT sensor_type, trigger_value, trigger_when_below, alert_message FROM Default_Thresholds")
                # add default thresholds
                defaults = cur.fetchall()
                for t in defaults:
                    cur.execute(
                        INSERT_DEFAULT_ALERT_THRESHOLDS,
                        (new_uuid,t["trigger_value"],t["sensor_type"],t["trigger_when_below"],t["alert_message"]))

                logger.info(f"Added new device {new_uuid}.")        
                return jsonify({"uuid": str(new_uuid)}), 201

    except Exception as e:
        logger.error(f"Failure registering device: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/telemetry", methods=["POST"])
def handle_telemetry():
    try:
        payload = Telemetry.model_validate(request.json)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO telemetry (device_id, sensor_values) VALUES (%s, %s) RETURNING created_at",
                    (payload.device_id, Json(payload.sensor_values)),
                )
                timestamp = cur.fetchone()["created_at"]
                handle_alert_logic(device_id=str(payload.device_id), sensor_values=payload.sensor_values, created_at=timestamp, conn=conn)
        
        return {"status": "ok"}, 200

    except Exception as e:
        logger.error(f"Failure in telemetry processing: {e}")
        return jsonify({"error": str(e)}), 500

# Basic get methods
@app.route("/api/devices", methods=["GET"])
def list_devices():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM Devices ORDER BY serial_number")
                devices = cur.fetchall()
                return jsonify(devices), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/devices/<device_id>/telemetry", methods=["GET"])
def get_telemetry_by_device(device_id):
    limit = request.args.get('limit', default=100, type=int)
    limit = min(limit, 1000)

    try:
        uuid.UUID(device_id)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, device_id, created_at, sensor_values FROM Telemetry
                    WHERE device_id = %s ORDER BY created_at DESC LIMIT %s;""", (device_id, limit))
                telemetry = cur.fetchall()
                return jsonify(telemetry), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/users", methods=["GET"])
def get_users():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, name, email FROM Users ORDER BY user_id ASC")
                return jsonify(cur.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.json
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO Users (name, email) VALUES (%s, %s) RETURNING user_id",
                    (data['name'], data['email'])
                )
                new_id = cur.fetchone()['user_id']
            conn.commit()
            return jsonify({"user_id": new_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
            
@app.route("/api/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.json
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE Users SET name = %s, email = %s WHERE user_id = %s",
                    (data['name'], data['email'], user_id)
                )
            conn.commit()
            return jsonify({"message": "Updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
            conn.commit()
            return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
