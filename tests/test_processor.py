import pytest
from unittest.mock import patch, MagicMock

from nutalert.processor import get_ups_data_and_alerts


class TestGetUpsDataAndAlerts:
    @patch("nutalert.processor.fetch_nut_ups_names")
    @patch("nutalert.processor.fetch_nut_data")
    @patch("nutalert.processor.parse_nut_data")
    def test_successful_data_retrieval(self, mock_parse, mock_fetch_data, mock_fetch_names):
        mock_fetch_names.return_value = ["ups1"]
        mock_fetch_data.return_value = "VAR ups1 battery.charge \"100\""
        mock_parse.return_value = {
            "ups1": {
                "battery.charge": 100,
                "ups.load": 20,
                "battery.runtime": 3600,
                "ups.status": "OL",
                "input.voltage": 120,
                "battery.voltage": 27.3,
            }
        }
        
        config = {
            "nut_server": {"host": "localhost", "port": 3493, "check_interval": 15},
            "notifications": {"enabled": False, "cooldown": 60, "urls": []},
            "ups_devices": {
                "ups1": {
                    "alert_mode": "basic",
                    "basic_alerts": {
                        "battery_charge": {"enabled": True, "min": 90, "message": "Low battery"},
                    },
                }
            },
        }
        
        nut_values, alerts, any_alerting, logs = get_ups_data_and_alerts(config)
        
        assert "ups1" in nut_values
        assert nut_values["ups1"]["battery.charge"] == 100
        assert "ups1" in alerts

    @patch("nutalert.processor.fetch_nut_ups_names")
    @patch("nutalert.processor.fetch_nut_data")
    @patch("nutalert.processor.parse_nut_data")
    def test_missing_ups_device(self, mock_parse, mock_fetch_data, mock_fetch_names):
        mock_fetch_names.return_value = ["ups1"]
        mock_fetch_data.return_value = "VAR ups1 battery.charge \"100\""
        mock_parse.return_value = {"ups1": {"battery.charge": 100}}
        
        config = {
            "nut_server": {"host": "localhost", "port": 3493, "check_interval": 15},
            "notifications": {"enabled": False, "cooldown": 60, "urls": []},
            "ups_devices": {
                "ups1": {"alert_mode": "basic", "basic_alerts": {}},
                "missing_ups": {"alert_mode": "basic", "basic_alerts": {}},
            },
        }
        
        nut_values, alerts, any_alerting, logs = get_ups_data_and_alerts(config)
        
        assert "missing_ups" in alerts
        alert_msg, is_alerting = alerts["missing_ups"]
        assert "not found" in alert_msg.lower()
        assert is_alerting is True

    def test_missing_nut_server_config(self):
        config = {}
        
        nut_values, alerts, any_alerting, logs = get_ups_data_and_alerts(config)
        
        assert any_alerting is True
        assert "configuration error" in alerts.lower()

    def test_missing_required_keys(self):
        config = {
            "nut_server": {"host": "localhost"},
        }
        
        nut_values, alerts, any_alerting, logs = get_ups_data_and_alerts(config)
        
        assert any_alerting is True

    @patch("nutalert.processor.fetch_nut_ups_names")
    def test_no_ups_devices_configured(self, mock_fetch_names):
        mock_fetch_names.return_value = ["ups1"]
        
        config = {
            "nut_server": {"host": "localhost", "port": 3493, "check_interval": 15},
            "notifications": {"enabled": False},
            "ups_devices": {},
        }
        
        nut_values, alerts, any_alerting, logs = get_ups_data_and_alerts(config)
        
        assert any_alerting is True

    @patch("nutalert.processor.fetch_nut_ups_names")
    @patch("nutalert.processor.fetch_nut_data")
    def test_no_data_from_server(self, mock_fetch_data, mock_fetch_names):
        mock_fetch_names.return_value = ["ups1"]
        mock_fetch_data.return_value = ""
        
        config = {
            "nut_server": {"host": "localhost", "port": 3493, "check_interval": 15},
            "notifications": {"enabled": False, "cooldown": 60},
            "ups_devices": {"ups1": {"alert_mode": "basic", "basic_alerts": {}}},
        }
        
        nut_values, alerts, any_alerting, logs = get_ups_data_and_alerts(config)
        
        assert "ups1" in alerts
        alert_msg, is_alerting = alerts["ups1"]
        assert "no data" in alert_msg.lower()
