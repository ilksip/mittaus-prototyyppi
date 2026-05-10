import logging
import uuid

from flask import Blueprint, jsonify, request
from psycopg.types.json import Json

from alert_logic import handle_alert_logic
from database import get_conn
from schemas import Telemetry

logger = logging.getLogger(__name__)
telemetry_bp = Blueprint("telemetry", __name__)

@telemetry_bp.route("/telemetry", methods=["POST"])
def handle_telemetry():
    try:
        payload = Telemetry.model_validate(request.json)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO telemetry (device_id, sensor_values)
                    VALUES (%s, %s)
                    RETURNING created_at
                    """, (payload.device_id, Json(payload.sensor_values)))
                timestamp = cur.fetchone()["created_at"]
                handle_alert_logic(
                    device_id=str(payload.device_id),
                    sensor_values=payload.sensor_values,
                    created_at=timestamp,
                    conn=conn)
        
        return {"status": "ok"}, 200

    except Exception as e:
        logger.error(f"Failure in telemetry processing: {e}")
        return jsonify({"error": str(e)}), 500

# Basic get methods


@telemetry_bp.route("/devices/<device_id>/telemetry", methods=["GET"])
def get_telemetry_by_device(device_id):
    limit = request.args.get("limit", default=100, type=int)
    limit = min(limit, 1000)

    try:
        uuid.UUID(device_id)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, device_id, created_at, sensor_values
                    FROM Telemetry
                    WHERE device_id = %s
                    ORDER BY created_at
                    DESC LIMIT %s;
                    """, (device_id, limit))
                telemetry = cur.fetchall()
                return jsonify(telemetry), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500