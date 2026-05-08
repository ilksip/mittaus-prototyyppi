import psycopg
from psycopg.types.json import Json
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

INSERT_DEFAULT_ALERT_THRESHOLDS="""
INSERT INTO Alert_Thresholds (
    device_id,
    trigger_value,
    sensor_type,
    trigger_when_below,
    alert_message
)
VALUES (%s, %s, %s, %s, %s);
"""

CHECK_RECENT_ALERT = """
SELECT * 
FROM Alert_History
WHERE device_id = %s
AND sensor_type = %s
AND threshold_value = %s
AND created_at >= NOW() - INTERVAL '24 hours'
LIMIT 1;
"""

INSERT_ALERT_EVENT = """
INSERT INTO Alert_History (
    device_id,
    sensor_type,
    threshold_value
)
VALUES (%s, %s, %s)
"""