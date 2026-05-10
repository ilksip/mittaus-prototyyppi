from flask import Blueprint, jsonify, request
from database import get_conn
import logging

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)

@users_bp.route("/users", methods=["GET"])
def get_users():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, name, email FROM Users ORDER BY user_id ASC")
                return jsonify(cur.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@users_bp.route("/users", methods=["POST"])
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
            
@users_bp.route("/users/<user_id>", methods=["PUT"])
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

@users_bp.route("/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
            conn.commit()
            return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400