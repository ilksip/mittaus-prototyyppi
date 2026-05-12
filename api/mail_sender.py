import logging
import smtplib
import threading
from email.message import EmailMessage

from config import format_timestamp, settings
from database import INSERT_ALERT_EVENT, get_conn

logger = logging.getLogger(__name__)

def send_email(*args, **kwargs):
    threading.Thread(target=send_mail_alerts, args=args, kwargs=kwargs).start()

EMAIL_ENABLED = settings.MAIL_SERVICE_ENABLED
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = int(settings.SMTP_PORT)
SMTP_USER = settings.SMTP_USER
SMTP_PASS = settings.SMTP_PASS

def send_mail_alerts(address: str, device_id: str, device_name: str, sensor_type: str, threshold_value: int, value: int, created_at, message: str):

    timestamp_str = format_timestamp(created_at)
    logger.debug("SENDING EMAIL")
    msg = EmailMessage()
    msg["Subject"] = f"Alert for device '{device_name}'"
    msg["From"] = SMTP_USER
    msg["To"] = address

    msg.set_content(f"""
        Id:     {device_id}
        Device: {device_name}
        Time:   {timestamp_str}

        Sensor value measured:  {sensor_type}:{value}{" %" if sensor_type == "fill_level" else ""}
        Msg:    {message}
        """)

    if EMAIL_ENABLED:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
    else:
        logger.info("Email Debug mode on: No email sent")
        logger.info(f"Sending mail from {SMTP_USER} to {address}...")
        logger.info(f"{timestamp_str}")

    logger.debug("Inserting new Alert Event!")
    with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(INSERT_ALERT_EVENT, (device_id, sensor_type, threshold_value))