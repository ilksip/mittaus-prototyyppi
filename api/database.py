import psycopg
from psycopg.rows import dict_row

from config import settings


def get_conn():
    connector = psycopg.connect(
        conninfo = settings.DATABASE_URL,
        row_factory = dict_row)
    return connector

INSERT_TELEMETRY = """
INSERT INTO telemetry (device_id,sensor_values)
VALUES (
    %(device_id)s,
    %(sensor_values)s
);
"""

INSERT_ALERT_EVENT = """
INSERT INTO Alert_History (
    device_id,
    sensor_type,
    threshold_value
)
VALUES (%s, %s, %s)
"""