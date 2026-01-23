import pytest
import sys
from unittest.mock import MagicMock, patch


sys.modules['nicegui'] = MagicMock()
sys.modules['nicegui.ui'] = MagicMock()
sys.modules['plotly'] = MagicMock()
sys.modules['plotly.graph_objects'] = MagicMock()


class MockState:
    def __init__(self, ups_names=None, ups_status=None):
        self.ups_names = ups_names or []
        self.ups_status = ups_status or {}


COLOR_THEME_MOCK = {
    "success": "#66BB6A",
    "warning": "#FFA726",
    "error": "#EF5350",
    "success_bg": "rgba(102, 187, 106, 0.2)",
    "error_bg": "rgba(239, 83, 80, 0.2)",
}


def get_overall_status_logic(ups_names, ups_status):
    has_error = False
    has_waiting = False
    for ups in ups_names:
        status = ups_status.get(ups, "waiting")
        if status == "error":
            has_error = True
        elif status == "waiting":
            has_waiting = True
    
    if has_error:
        return "error", "warning", COLOR_THEME_MOCK["warning"], "Check status", COLOR_THEME_MOCK["error_bg"]
    elif has_waiting:
        return "waiting", "hourglass_empty", COLOR_THEME_MOCK["warning"], "Checking...", COLOR_THEME_MOCK["error_bg"]
    else:
        return "ok", "check_circle", COLOR_THEME_MOCK["success"], "Devices healthy", COLOR_THEME_MOCK["success_bg"]


def get_load_gauge_color(value, warn, high):
    if value > high:
        return COLOR_THEME_MOCK["error"]
    elif value > warn:
        return COLOR_THEME_MOCK["warning"]
    else:
        return COLOR_THEME_MOCK["success"]


def get_charge_gauge_color(value, warn, high):
    if value < high:
        return COLOR_THEME_MOCK["error"]
    elif value < warn:
        return COLOR_THEME_MOCK["warning"]
    else:
        return COLOR_THEME_MOCK["success"]


def get_runtime_gauge_color(value, warn, high):
    if value < high:
        return COLOR_THEME_MOCK["error"]
    elif value < warn:
        return COLOR_THEME_MOCK["warning"]
    else:
        return COLOR_THEME_MOCK["success"]


def get_voltage_gauge_color(value, nominal, warn_deviation, high_deviation):
    min_voltage = nominal - warn_deviation
    max_voltage = nominal + warn_deviation
    display_min = nominal - high_deviation
    display_max = nominal + high_deviation
    
    if min_voltage <= value <= max_voltage:
        return COLOR_THEME_MOCK["success"]
    elif display_min <= value < min_voltage or max_voltage < value <= display_max:
        return COLOR_THEME_MOCK["warning"]
    else:
        return COLOR_THEME_MOCK["error"]


class TestGetOverallStatus:
    def test_all_devices_ok(self):
        status, icon, color, label, bg = get_overall_status_logic(
            ["ups1", "ups2"],
            {"ups1": "ok", "ups2": "ok"}
        )
        
        assert status == "ok"
        assert icon == "check_circle"
        assert label == "Devices healthy"

    def test_one_device_error(self):
        status, icon, color, label, bg = get_overall_status_logic(
            ["ups1", "ups2"],
            {"ups1": "ok", "ups2": "error"}
        )
        
        assert status == "error"
        assert icon == "warning"
        assert label == "Check status"

    def test_device_waiting(self):
        status, icon, color, label, bg = get_overall_status_logic(
            ["ups1", "ups2"],
            {"ups1": "ok", "ups2": "waiting"}
        )
        
        assert status == "waiting"
        assert icon == "hourglass_empty"
        assert label == "Checking..."

    def test_error_takes_precedence_over_waiting(self):
        status, icon, color, label, bg = get_overall_status_logic(
            ["ups1", "ups2", "ups3"],
            {"ups1": "ok", "ups2": "waiting", "ups3": "error"}
        )
        
        assert status == "error"
        assert label == "Check status"

    def test_no_devices(self):
        status, icon, color, label, bg = get_overall_status_logic([], {})
        
        assert status == "ok"
        assert label == "Devices healthy"

    def test_missing_status_defaults_to_waiting(self):
        status, icon, color, label, bg = get_overall_status_logic(
            ["ups1", "ups2"],
            {"ups1": "ok"}
        )
        
        assert status == "waiting"


class TestGaugeThresholds:
    def test_load_gauge_green_zone(self):
        color = get_load_gauge_color(value=50, warn=80, high=100)
        assert color == COLOR_THEME_MOCK["success"]

    def test_load_gauge_yellow_zone(self):
        color = get_load_gauge_color(value=90, warn=80, high=100)
        assert color == COLOR_THEME_MOCK["warning"]

    def test_load_gauge_red_zone(self):
        color = get_load_gauge_color(value=105, warn=80, high=100)
        assert color == COLOR_THEME_MOCK["error"]

    def test_charge_gauge_green_zone(self):
        color = get_charge_gauge_color(value=80, warn=35, high=15)
        assert color == COLOR_THEME_MOCK["success"]

    def test_charge_gauge_yellow_zone(self):
        color = get_charge_gauge_color(value=25, warn=35, high=15)
        assert color == COLOR_THEME_MOCK["warning"]

    def test_charge_gauge_red_zone(self):
        color = get_charge_gauge_color(value=10, warn=35, high=15)
        assert color == COLOR_THEME_MOCK["error"]

    def test_runtime_gauge_green_zone(self):
        color = get_runtime_gauge_color(value=60, warn=15, high=5)
        assert color == COLOR_THEME_MOCK["success"]

    def test_runtime_gauge_yellow_zone(self):
        color = get_runtime_gauge_color(value=10, warn=15, high=5)
        assert color == COLOR_THEME_MOCK["warning"]

    def test_runtime_gauge_red_zone(self):
        color = get_runtime_gauge_color(value=3, warn=15, high=5)
        assert color == COLOR_THEME_MOCK["error"]

    def test_voltage_gauge_green_zone(self):
        color = get_voltage_gauge_color(value=120, nominal=120, warn_deviation=10, high_deviation=15)
        assert color == COLOR_THEME_MOCK["success"]

    def test_voltage_gauge_yellow_zone_low(self):
        color = get_voltage_gauge_color(value=108, nominal=120, warn_deviation=10, high_deviation=15)
        assert color == COLOR_THEME_MOCK["warning"]

    def test_voltage_gauge_yellow_zone_high(self):
        color = get_voltage_gauge_color(value=132, nominal=120, warn_deviation=10, high_deviation=15)
        assert color == COLOR_THEME_MOCK["warning"]

    def test_voltage_gauge_boundary_warn_low(self):
        color = get_voltage_gauge_color(value=110, nominal=120, warn_deviation=10, high_deviation=15)
        assert color == COLOR_THEME_MOCK["success"]

    def test_voltage_gauge_boundary_warn_high(self):
        color = get_voltage_gauge_color(value=130, nominal=120, warn_deviation=10, high_deviation=15)
        assert color == COLOR_THEME_MOCK["success"]

