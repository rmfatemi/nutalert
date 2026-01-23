import pytest
from unittest.mock import patch, MagicMock

from nutalert.alert import (
    prepare_ups_env,
    check_battery_charge,
    check_runtime,
    check_load,
    check_input_voltage,
    check_ups_status,
    check_basic_alerts,
    check_formula_alert,
    should_alert,
)


class TestPrepareUpsEnv:
    def test_prepare_env_with_full_data(self):
        nut_values = {
            "ups.load": 25,
            "battery.charge": 100,
            "battery.runtime": 3600,
            "battery.voltage": 27.3,
            "input.voltage": 120.5,
            "ups.status": "OL",
        }
        
        env = prepare_ups_env(nut_values)
        
        assert env["ups_load"] == 25
        assert env["battery_charge"] == 100
        assert env["battery_runtime"] == 3600
        assert env["actual_runtime_minutes"] == 60.0
        assert env["battery_voltage"] == 27.3
        assert env["input_voltage"] == 120.5
        assert env["ups_status"] == "ol"

    def test_prepare_env_with_missing_data(self):
        nut_values = {}
        
        env = prepare_ups_env(nut_values)
        
        assert env["ups_load"] == 0
        assert env["battery_charge"] == 0
        assert env["battery_runtime"] == 0
        assert env["actual_runtime_minutes"] == 0.0
        assert env["battery_voltage"] == 0
        assert env["input_voltage"] == 0
        assert env["ups_status"] == ""


class TestCheckBatteryCharge:
    def test_battery_charge_below_threshold(self):
        basic_alerts = {
            "battery_charge": {"min": 90, "message": "Low battery"}
        }
        env = {"battery_charge": 80}
        
        result = check_battery_charge(basic_alerts, env)
        
        assert result == "Low battery"

    def test_battery_charge_above_threshold(self):
        basic_alerts = {
            "battery_charge": {"min": 90, "message": "Low battery"}
        }
        env = {"battery_charge": 100}
        
        result = check_battery_charge(basic_alerts, env)
        
        assert result is None

    def test_battery_charge_missing_min(self):
        basic_alerts = {"battery_charge": {"message": "Low battery"}}
        env = {"battery_charge": 80}
        
        result = check_battery_charge(basic_alerts, env)
        
        assert "config error" in result.lower()


class TestCheckRuntime:
    def test_runtime_below_threshold(self):
        basic_alerts = {
            "runtime": {"min": 15, "message": "Low runtime"}
        }
        env = {"actual_runtime_minutes": 10}
        
        result = check_runtime(basic_alerts, env)
        
        assert "Low runtime" in result
        assert "10.0min" in result

    def test_runtime_above_threshold(self):
        basic_alerts = {
            "runtime": {"min": 15, "message": "Low runtime"}
        }
        env = {"actual_runtime_minutes": 60}
        
        result = check_runtime(basic_alerts, env)
        
        assert result is None


class TestCheckLoad:
    def test_load_above_threshold(self):
        basic_alerts = {
            "load": {"max": 50, "message": "High load"}
        }
        env = {"ups_load": 60}
        
        result = check_load(basic_alerts, env)
        
        assert "High load" in result
        assert "60.0%" in result

    def test_load_below_threshold(self):
        basic_alerts = {
            "load": {"max": 50, "message": "High load"}
        }
        env = {"ups_load": 30}
        
        result = check_load(basic_alerts, env)
        
        assert result is None


class TestCheckInputVoltage:
    def test_voltage_below_min(self):
        basic_alerts = {
            "input_voltage": {"min": 110, "max": 130, "message": "Bad voltage"}
        }
        env = {"input_voltage": 100}
        
        result = check_input_voltage(basic_alerts, env)
        
        assert "Bad voltage" in result

    def test_voltage_above_max(self):
        basic_alerts = {
            "input_voltage": {"min": 110, "max": 130, "message": "Bad voltage"}
        }
        env = {"input_voltage": 140}
        
        result = check_input_voltage(basic_alerts, env)
        
        assert "Bad voltage" in result

    def test_voltage_in_range(self):
        basic_alerts = {
            "input_voltage": {"min": 110, "max": 130, "message": "Bad voltage"}
        }
        env = {"input_voltage": 120}
        
        result = check_input_voltage(basic_alerts, env)
        
        assert result is None

    def test_voltage_zero(self):
        basic_alerts = {
            "input_voltage": {"min": 110, "max": 130, "message": "Bad voltage"}
        }
        env = {"input_voltage": 0}
        
        result = check_input_voltage(basic_alerts, env)
        
        assert result is None


class TestCheckUpsStatus:
    def test_status_not_acceptable(self):
        basic_alerts = {
            "ups_status": {"acceptable": ["ol", "online"], "message": "Bad status"}
        }
        env = {"ups_status": "ob"}
        
        result = check_ups_status(basic_alerts, env)
        
        assert "Bad status" in result
        assert "ob" in result

    def test_status_acceptable(self):
        basic_alerts = {
            "ups_status": {"acceptable": ["ol", "online"], "message": "Bad status"}
        }
        env = {"ups_status": "ol"}
        
        result = check_ups_status(basic_alerts, env)
        
        assert result is None

    def test_status_empty(self):
        basic_alerts = {
            "ups_status": {"acceptable": ["ol", "online"], "message": "Bad status"}
        }
        env = {"ups_status": ""}
        
        result = check_ups_status(basic_alerts, env)
        
        assert result is None


class TestCheckBasicAlerts:
    def test_multiple_alerts_triggered(self):
        config = {
            "basic_alerts": {
                "battery_charge": {"enabled": True, "min": 90, "message": "Low battery"},
                "load": {"enabled": True, "max": 50, "message": "High load"},
                "runtime": {"enabled": False, "min": 15, "message": "Low runtime"},
            }
        }
        env = {"battery_charge": 80, "ups_load": 60, "actual_runtime_minutes": 5}
        
        result = check_basic_alerts(config, env)
        
        assert len(result) == 2
        assert any("Low battery" in r for r in result)
        assert any("High load" in r for r in result)

    def test_no_alerts_triggered(self):
        config = {
            "basic_alerts": {
                "battery_charge": {"enabled": True, "min": 50, "message": "Low battery"},
                "load": {"enabled": True, "max": 80, "message": "High load"},
            }
        }
        env = {"battery_charge": 100, "ups_load": 20}
        
        result = check_basic_alerts(config, env)
        
        assert len(result) == 0


class TestCheckFormulaAlert:
    def test_formula_triggers_alert(self):
        config = {
            "formula_alert": {
                "expression": "battery_charge < 90 and ups_load > 20",
                "message": "Alert: {battery_charge}%, {ups_load}%",
            }
        }
        env = {"battery_charge": 80, "ups_load": 30, "actual_runtime_minutes": 60}
        
        is_alerting, message = check_formula_alert(config, env)
        
        assert is_alerting is True
        assert "80%" in message
        assert "30%" in message

    def test_formula_no_alert(self):
        config = {
            "formula_alert": {
                "expression": "battery_charge < 90 and ups_load > 50",
                "message": "Alert",
            }
        }
        env = {"battery_charge": 100, "ups_load": 20, "actual_runtime_minutes": 60}
        
        is_alerting, message = check_formula_alert(config, env)
        
        assert is_alerting is False
        assert "UPS Ok" in message

    def test_formula_invalid_expression(self):
        config = {
            "formula_alert": {
                "expression": "invalid_expression!!!",
                "message": "Alert",
            }
        }
        env = {"battery_charge": 80, "ups_load": 30, "actual_runtime_minutes": 60}
        
        is_alerting, message = check_formula_alert(config, env)
        
        assert is_alerting is True
        assert "error" in message.lower()


class TestShouldAlert:
    def test_basic_mode_with_alert(self):
        nut_values = {"battery.charge": 80, "ups.load": 20, "battery.runtime": 3600, "ups.status": "OL"}
        config = {
            "alert_mode": "basic",
            "basic_alerts": {
                "battery_charge": {"enabled": True, "min": 90, "message": "Low battery"},
            },
        }
        
        is_alerting, message = should_alert(nut_values, config)
        
        assert is_alerting is True
        assert "Low battery" in message

    def test_basic_mode_no_alert(self):
        nut_values = {"battery.charge": 100, "ups.load": 20, "battery.runtime": 3600, "ups.status": "OL"}
        config = {
            "alert_mode": "basic",
            "basic_alerts": {
                "battery_charge": {"enabled": True, "min": 90, "message": "Low battery"},
            },
        }
        
        is_alerting, message = should_alert(nut_values, config)
        
        assert is_alerting is False
        assert "UPS Ok" in message

    def test_formula_mode_with_alert(self):
        nut_values = {"battery.charge": 80, "ups.load": 30, "battery.runtime": 600}
        config = {
            "alert_mode": "formula",
            "formula_alert": {
                "expression": "battery_charge < 90 and ups_load > 20",
                "message": "Formula alert",
            },
        }
        
        is_alerting, message = should_alert(nut_values, config)
        
        assert is_alerting is True

    def test_unknown_alert_mode(self):
        nut_values = {"battery.charge": 100}
        config = {"alert_mode": "unknown_mode"}
        
        is_alerting, message = should_alert(nut_values, config)
        
        assert is_alerting is True
        assert "unknown alert mode" in message.lower()
