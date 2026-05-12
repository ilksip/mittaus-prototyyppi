import logging

from flask import Blueprint, jsonify, request

from database import get_conn

logger = logging.getLogger(__name__)

contacts_bp = Blueprint("contacts", __name__)

@contacts_bp.route("/contacts", methods=["GET"])
def get_contacts():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT contact_id, name, email
                    FROM Contacts
                    ORDER BY contact_id ASC
                    """)
                return jsonify(cur.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@contacts_bp.route("/contacts", methods=["POST"])
def create_contact():
    data = request.json
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO Contacts (name, email)
                    VALUES (%s, %s)
                    RETURNING contact_id
                    """, (data["name"], data["email"]))
                new_id = cur.fetchone()["contact_id"]
            conn.commit()
            return jsonify({"contact_id": new_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
            
@contacts_bp.route("/contacts/<contact_id>", methods=["PUT"])
def update_contact(contact_id):
    data = request.json
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE Contacts
                    SET name = %s, email = %s
                    WHERE contact_id = %s
                    """, (data["name"], data["email"], contact_id))
            conn.commit()
            return jsonify({"message": "Updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@contacts_bp.route("/contacts/<contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM contacts
                    WHERE contact_id = %s
                    """, (contact_id,))
            conn.commit()
            return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400