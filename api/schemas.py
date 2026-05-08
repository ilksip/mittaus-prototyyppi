from pydantic import BaseModel
from typing import Dict
from uuid import UUID
from datetime import datetime

class Telemetry(BaseModel):
    device_id: UUID
    sensor_values: Dict[str, float]

class Device(BaseModel):
    mac_address: str