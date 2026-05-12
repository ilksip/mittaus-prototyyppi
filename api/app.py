import logging

from flask import Flask

from config import setup_app_logging
from routes.contacts import contacts_bp
from routes.devices import devices_bp
from routes.telemetry import telemetry_bp

url_prefix = "/api"
setup_app_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.register_blueprint(devices_bp, url_prefix=url_prefix)
app.register_blueprint(contacts_bp, url_prefix=url_prefix)
app.register_blueprint(telemetry_bp, url_prefix=url_prefix)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
