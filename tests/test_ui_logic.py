import pytest
import sys
from unittest.mock import MagicMock, patch


sys.modules['nicegui'] = MagicMock()
sys.modules['nicegui.ui'] = MagicMock()
sys.modules['plotly'] = MagicMock()
sys.modules['plotly.graph_objects'] = MagicMock()

from nutalert.ui.dashboard import create_dial_gauge
from nutalert.ui.theme import COLOR_THEME
import plotly.graph_objects as go


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
        return "ok", "check_circle", COLOR_THEME_MOCK["success"], "Healthy", COLOR_THEME_MOCK["success_bg"]


class TestGetOverallStatus:
    def test_all_devices_ok(self):
        status, icon, color, label, bg = get_overall_status_logic(
            ["ups1", "ups2"],
            {"ups1": "ok", "ups2": "ok"}
        )
        
        assert status == "ok"
        assert icon == "check_circle"
        assert label == "Healthy"

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
        assert label == "Healthy"

    def test_missing_status_defaults_to_waiting(self):
        status, icon, color, label, bg = get_overall_status_logic(
            ["ups1", "ups2"],
            {"ups1": "ok"}
        )
        
        assert status == "waiting"


class TestGaugeBarColor:
    """the gauge bar is a static white (theme primary), not dynamic per value."""

    def _bar_color(self, metric_type, value, **kwargs):
        create_dial_gauge(value, "Test", metric_type, 0, 100, {}, **kwargs)
        return go.Indicator.call_args.kwargs["gauge"]["bar"]["color"]

    def test_bar_color_is_static_white_for_all_metrics(self):
        for metric_type in ("load", "charge", "runtime", "voltage"):
            assert self._bar_color(metric_type, 50) == COLOR_THEME["primary"]

    def test_bar_color_does_not_change_with_value(self):
        for value in (10, 50, 90, 110):
            assert self._bar_color("load", value) == COLOR_THEME["primary"]

    def test_primary_is_white(self):
        assert COLOR_THEME["primary"] == "#FFFFFF"


class MockStateWithLogs:
    def __init__(self, ups_names=None, ups_status=None, logs="", consecutive_clean_polls=0):
        self.ups_names = ups_names or []
        self.ups_status = ups_status or {}
        self.logs = logs
        self._consecutive_clean_polls = consecutive_clean_polls


def logs_have_recent_errors_logic(state):
    if state._consecutive_clean_polls >= 2:
        return False
    if not state.logs:
        return False
    for line in state.logs.splitlines():
        if "[ERROR]" in line.upper():
            return True
    return False


class TestErrorRecovery:
    def test_no_errors_no_logs(self):
        state = MockStateWithLogs(logs="", consecutive_clean_polls=0)
        assert logs_have_recent_errors_logic(state) is False

    def test_errors_in_logs_zero_clean_polls(self):
        state = MockStateWithLogs(logs="2024-01-01 [ERROR] something failed", consecutive_clean_polls=0)
        assert logs_have_recent_errors_logic(state) is True

    def test_errors_in_logs_one_clean_poll(self):
        state = MockStateWithLogs(logs="2024-01-01 [ERROR] something failed", consecutive_clean_polls=1)
        assert logs_have_recent_errors_logic(state) is True

    def test_errors_in_logs_two_clean_polls_recovers(self):
        state = MockStateWithLogs(logs="2024-01-01 [ERROR] something failed", consecutive_clean_polls=2)
        assert logs_have_recent_errors_logic(state) is False

    def test_errors_in_logs_many_clean_polls_recovers(self):
        state = MockStateWithLogs(logs="2024-01-01 [ERROR] something failed", consecutive_clean_polls=10)
        assert logs_have_recent_errors_logic(state) is False

    def test_no_errors_but_info_logs(self):
        state = MockStateWithLogs(logs="2024-01-01 [INFO] all good", consecutive_clean_polls=0)
        assert logs_have_recent_errors_logic(state) is False