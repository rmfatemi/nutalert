from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


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
    timeout: int = Field(gt=0)
    check_interval: int = Field(ge=5)


class FormulaAlert(BaseModel):
    expression: str
    message: str


class NotificationsConfig(BaseModel):
    enabled: bool
    cooldown: int
    urls: List[Dict[str, Any]]


class AppConfig(BaseModel):
    nut_server: NutServerConfig
    alert_mode: str
    basic_alerts: Optional[BasicAlerts] = None
    formula_alert: Optional[FormulaAlert] = None
    notifications: Optional[NotificationsConfig] = None
