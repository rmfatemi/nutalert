from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class MinMaxAlert(BaseModel):
    enabled: bool = False
    min: Optional[float] = None
    max: Optional[float] = None
    message: Optional[str] = None


class StatusAlert(BaseModel):
    enabled: bool = False
    acceptable: List[str] = []
    message: Optional[str] = None
    alert_when_status_changed: bool = False


class BasicAlerts(BaseModel):
    battery_charge: Optional[MinMaxAlert] = None
    runtime: Optional[MinMaxAlert] = None
    load: Optional[MinMaxAlert] = None
    input_voltage: Optional[MinMaxAlert] = None
    ups_status: Optional[StatusAlert] = None


class NutServerConfig(BaseModel):
    host: str
    port: int = Field(gt=0, le=65535)
    check_interval: int = Field(ge=5)


class FormulaAlert(BaseModel):
    message: str
    expression: str


class NotificationsConfig(BaseModel):
    enabled: bool
    cooldown: int
    urls: List[Dict[str, Any]]


class AppConfig(BaseModel):
    ups_devices: Dict[str, Any]
    nut_server: NutServerConfig
    notifications: Optional[NotificationsConfig] = None
