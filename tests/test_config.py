import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from nutalert.config import (
    load_config, save_config, DEFAULT_CONFIG, DEFAULT_UPS_CONFIG,
    _is_old_format, _migrate_v1_to_v2, CURRENT_CONFIG_VERSION
)


class TestLoadConfig:
    @patch("nutalert.config.fetch_nut_ups_names")
    @patch("nutalert.config.CONFIG_PATH", "/tmp/nonexistent_config.yaml")
    def test_load_config_no_file(self, mock_fetch):
        mock_fetch.return_value = ["test_ups"]
        
        with patch("nutalert.config.os.path.exists", return_value=False):
            with patch("nutalert.config.save_config") as mock_save:
                config = load_config()
        
        assert "nut_server" in config
        assert "notifications" in config
        assert "ups_devices" in config
        assert "test_ups" in config["ups_devices"]

    @patch("nutalert.config.fetch_nut_ups_names")
    def test_load_config_with_existing_file(self, mock_fetch):
        mock_fetch.return_value = ["ups1"]
        
        test_config = """
nut_server:
  host: 192.168.1.1
  port: 3493
  check_interval: 30
notifications:
  enabled: false
  cooldown: 120
  urls: []
ups_devices:
  ups1:
    alert_mode: formula
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(test_config)
            temp_path = f.name
        
        try:
            with patch("nutalert.config.CONFIG_PATH", temp_path):
                config = load_config()
            
            assert config["nut_server"]["host"] == "192.168.1.1"
            assert config["nut_server"]["check_interval"] == 30
            assert config["notifications"]["enabled"] is False
            assert "ups1" in config["ups_devices"]
        finally:
            os.unlink(temp_path)

    @patch("nutalert.config.fetch_nut_ups_names")
    def test_load_config_adds_new_ups(self, mock_fetch):
        mock_fetch.return_value = ["ups1", "ups2"]
        
        test_config = """
nut_server:
  host: localhost
  port: 3493
  check_interval: 15
notifications:
  enabled: true
  cooldown: 60
  urls: []
ups_devices:
  ups1:
    alert_mode: basic
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(test_config)
            temp_path = f.name
        
        try:
            with patch("nutalert.config.CONFIG_PATH", temp_path):
                with patch("nutalert.config.save_config"):
                    config = load_config()
            
            assert "ups1" in config["ups_devices"]
            assert "ups2" in config["ups_devices"]
            assert config["ups_devices"]["ups1"]["alert_mode"] == "basic"
            assert config["ups_devices"]["ups2"]["alert_mode"] == "basic"
        finally:
            os.unlink(temp_path)

    @patch("nutalert.config.fetch_nut_ups_names")
    def test_load_config_keeps_offline_ups(self, mock_fetch):
        mock_fetch.return_value = ["new_ups"]
        
        test_config = """
nut_server:
  host: localhost
  port: 3493
  check_interval: 15
notifications:
  enabled: true
  cooldown: 60
  urls: []
ups_devices:
  old_ups_1:
    alert_mode: basic
  old_ups_2:
    alert_mode: formula
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(test_config)
            temp_path = f.name
        
        try:
            with patch("nutalert.config.CONFIG_PATH", temp_path):
                with patch("nutalert.config._save_config_file"):
                    config = load_config()

            assert "old_ups_1" in config["ups_devices"]
            assert "old_ups_2" in config["ups_devices"]
            assert "new_ups" in config["ups_devices"]
            assert len(config["ups_devices"]) == 3
        finally:
            os.unlink(temp_path)


class TestSaveConfig:
    def test_save_config_success(self):
        config = {
            "nut_server": {"host": "localhost", "port": 3493},
            "ups_devices": {"ups": {"alert_mode": "basic"}},
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = f.name
        
        try:
            with patch("nutalert.config.CONFIG_PATH", temp_path):
                result = save_config(config)
            
            assert "successfully" in result.lower()
            
            with open(temp_path, "r") as f:
                content = f.read()
            assert "localhost" in content
            assert "ups" in content
        finally:
            os.unlink(temp_path)

    def test_save_config_failure(self):
        config = {"test": "data"}
        
        with patch("nutalert.config.CONFIG_PATH", "/nonexistent/path/config.yaml"):
            result = save_config(config)
        
        assert "failed" in result.lower()


class TestDefaultConfig:
    def test_default_config_structure(self):
        assert "nut_server" in DEFAULT_CONFIG
        assert "notifications" in DEFAULT_CONFIG
        assert "ups_devices" in DEFAULT_CONFIG
        assert "config_version" in DEFAULT_CONFIG
        
        assert "host" in DEFAULT_CONFIG["nut_server"]
        assert "port" in DEFAULT_CONFIG["nut_server"]
        assert "check_interval" in DEFAULT_CONFIG["nut_server"]

    def test_default_ups_config_structure(self):
        assert "alert_mode" in DEFAULT_UPS_CONFIG
        assert "gauge_settings" in DEFAULT_UPS_CONFIG
        assert "basic_alerts" in DEFAULT_UPS_CONFIG
        assert "formula_alert" in DEFAULT_UPS_CONFIG
        
        assert "load" in DEFAULT_UPS_CONFIG["gauge_settings"]
        assert "charge_remaining" in DEFAULT_UPS_CONFIG["gauge_settings"]
        assert "runtime" in DEFAULT_UPS_CONFIG["gauge_settings"]
        assert "voltage" in DEFAULT_UPS_CONFIG["gauge_settings"]


class TestConfigMigration:
    def test_is_old_format_with_top_level_alerts(self):
        old_config = {
            "nut_server": {"host": "localhost", "port": 3493},
            "notifications": {"enabled": True, "cooldown": 60, "urls": []},
            "alert_mode": "basic",
            "basic_alerts": {"battery_charge": {"enabled": True, "min": 90}},
            "formula_alert": {"expression": "test", "message": "test"},
        }
        assert _is_old_format(old_config) is True

    def test_is_old_format_with_version(self):
        new_config = {
            "config_version": 2,
            "nut_server": {"host": "localhost", "port": 3493},
            "notifications": {"enabled": True, "cooldown": 60, "urls": []},
            "ups_devices": {},
        }
        assert _is_old_format(new_config) is False

    def test_is_old_format_no_ups_devices(self):
        old_config = {
            "nut_server": {"host": "localhost", "port": 3493},
            "check_interval": 15,
        }
        assert _is_old_format(old_config) is True

    def test_migrate_v1_to_v2_preserves_nut_server(self):
        old_config = {
            "nut_server": {"host": "192.168.1.100", "port": 3493, "timeout": 5},
            "check_interval": 30,
            "notifications": {"enabled": True, "cooldown": 120, "urls": []},
            "alert_mode": "formula",
            "basic_alerts": {"battery_charge": {"enabled": True, "min": 80}},
            "formula_alert": {"expression": "test expr", "message": "test msg"},
        }
        
        new_config = _migrate_v1_to_v2(old_config)
        
        assert new_config["config_version"] == CURRENT_CONFIG_VERSION
        assert new_config["nut_server"]["host"] == "192.168.1.100"
        assert new_config["nut_server"]["check_interval"] == 30
        assert new_config["notifications"]["cooldown"] == 120

    def test_migrate_v1_to_v2_creates_device_config(self):
        old_config = {
            "nut_server": {"host": "localhost", "port": 3493},
            "alert_mode": "formula",
            "basic_alerts": {"battery_charge": {"enabled": False, "min": 75}},
            "formula_alert": {"expression": "custom_expr", "message": "custom_msg"},
        }
        
        new_config = _migrate_v1_to_v2(old_config)
        
        assert "_migrated_device_config" in new_config
        device_cfg = new_config["_migrated_device_config"]
        assert device_cfg["alert_mode"] == "formula"
        assert device_cfg["basic_alerts"]["battery_charge"]["min"] == 75
        assert device_cfg["formula_alert"]["expression"] == "custom_expr"

    @patch("nutalert.config.fetch_nut_ups_names")
    @patch("nutalert.config._backup_config")
    @patch("nutalert.config._save_config_file")
    def test_load_config_migrates_old_format(self, mock_save, mock_backup, mock_fetch):
        mock_fetch.return_value = ["my_ups"]
        mock_backup.return_value = "/tmp/config.yaml.bak"
        
        old_config = """
nut_server:
  host: docker.home
  port: 3493
  timeout: 3
notifications:
  enabled: true
  cooldown: 60
  urls:
  - url: tgram://token/chatid
    enabled: true
check_interval: 15
alert_mode: formula
basic_alerts:
  battery_charge:
    enabled: true
    min: 90
    message: battery charge below minimum threshold
formula_alert:
  expression: battery_charge < 90
  message: alert message
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(old_config)
            temp_path = f.name
        
        try:
            with patch("nutalert.config.CONFIG_PATH", temp_path):
                config = load_config()
            
            assert config["config_version"] == CURRENT_CONFIG_VERSION
            assert "my_ups" in config["ups_devices"]
            assert config["ups_devices"]["my_ups"]["alert_mode"] == "formula"
            assert config["ups_devices"]["my_ups"]["formula_alert"]["expression"] == "battery_charge < 90"
            mock_backup.assert_called_once()
        finally:
            os.unlink(temp_path)
