CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE Devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mac_address TEXT UNIQUE NOT NULL,
    device_name TEXT DEFAULT 'New device',
    serial_number SERIAL,
    firmware_version TEXT DEFAULT '1.0',
    height_buffer INTEGER NOT NULL DEFAULT 5,
    bin_height INTEGER NOT NULL CHECK (bin_height > 0) DEFAULT 75,
    alerts_enabled BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE Contacts (
    contact_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE Telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sensor_values JSONB NOT NULL,

    CONSTRAINT fk_telemetry_device
        FOREIGN KEY (device_id)
        REFERENCES Devices(device_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_telemetry_device_timestamp
    ON Telemetry(device_id, created_at DESC);

CREATE INDEX idx_telemetry_sensor_values
    ON Telemetry USING GIN (sensor_values);

CREATE TABLE Alert_Recipients (
    device_id UUID NOT NULL,
    contact_id INTEGER NOT NULL,

    PRIMARY KEY (device_id, contact_id),
    
    CONSTRAINT fk_alertrec_device
        FOREIGN KEY (device_id)
        REFERENCES Devices(device_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_alertrec_contact
        FOREIGN KEY (contact_id)
        REFERENCES Contacts(contact_id)
        ON DELETE CASCADE
);

CREATE TYPE sensor AS ENUM ('fill_level','temperature','weight','battery');
CREATE TABLE Alert_Thresholds (
    threshold_id SERIAL,
    device_id UUID NOT NULL,
    trigger_value INTEGER NOT NULL,
    sensor_type sensor NOT NULL,
    trigger_when_below BOOLEAN NOT NULL,
    alert_message TEXT NOT NULL,

    PRIMARY KEY (threshold_id),

    CONSTRAINT fk_threshold_device
        FOREIGN KEY (device_id)
        REFERENCES Devices(device_id)
        ON DELETE CASCADE
);
CREATE TABLE Default_Thresholds (
    default_id SERIAL PRIMARY KEY,
    sensor_type sensor NOT NULL,
    trigger_value INTEGER NOT NULL,
    trigger_when_below BOOLEAN NOT NULL,
    alert_message TEXT NOT NULL
);
INSERT INTO Default_Thresholds (sensor_type, trigger_value, trigger_when_below, alert_message) VALUES
('fill_level', 50, false, 'Säiliö 50% täynnä. Tyhjennys tulee pian ajankohtaiseksi.'),
('fill_level', 75, false, 'Säiliö 75% täynnä. Tyhjennys suositeltavaa.'),
('fill_level', 90, false, 'Säiliö 90% täynnä. Tyhjennä pian!'),
('fill_level', 99, false, 'Säiliö yli 99% täynnä! Tyhjennä heti!!!.'),
('battery', 20, true, 'Akun varaus vähissä (alle 20%).');

CREATE INDEX idx_threshold_device
    ON Alert_Thresholds(device_id);

CREATE TABLE Alert_History (
    alert_id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL,
    sensor_type TEXT,
    threshold_value NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_alerthistory_device
        FOREIGN KEY (device_id)
        REFERENCES Devices(device_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_alerthistory_device_created_at
    ON Alert_History(device_id, sensor_type, threshold_value, created_at DESC);
