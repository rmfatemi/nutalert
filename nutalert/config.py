import os
import copy

from io import StringIO
from typing import Dict, Any

from ruamel.yaml import YAML

from nutalert.fetcher import fetch_nut_ups_names
from nutalert.utils import setup_logger


logger = setup_logger("config")

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml")))

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.default_flow_style = False


DEFAULT_UPS_CONFIG: Dict[str, Any] = {
    "alert_mode": "basic",
    "gauge_settings": {
        "load": {"warn_threshold": 80, "high_threshold": 100},
        "charge_remaining": {"warn_threshold": 35, "high_threshold": 15},
        "runtime": {"warn_threshold": 15, "high_threshold": 5},
        "voltage": {"nominal": 120, "warn_deviation": 10, "high_deviation": 15},
    },
    "basic_alerts": {
        "battery_charge": {
            "enabled": True,
            "min": 90,
            "message": "UPS battery charge below minimum threshold",
        },
        "runtime": {
            "enabled": True,
            "min": 15,
            "message": "UPS runtime below minimum threshold",
        },
        "load": {
            "enabled": True,
            "max": 50,
            "message": "UPS load exceeds maximum threshold",
        },
        "input_voltage": {
            "enabled": False,
            "min": 110.0,
            "max": 130.0,
            "message": "UPS input voltage outside acceptable range",
        },
        "ups_status": {
            "enabled": True,
            "acceptable": ["ol", "online"],
            "alert_when_status_changed": False,
            "message": "UPS status not in acceptable list",
        },
    },
    "formula_alert": {
        "expression": "(battery_charge < 90 or actual_runtime_minutes < 20) and ups_load > 20",
        "message": "UPS load: {ups_load}%, charge: {battery_charge}%, runtime: {actual_runtime_minutes:.1f} mins",
    },
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "nut_server": {
        "host": "127.0.0.1",
        "port": 3493,
        "check_interval": 15,
    },
    "notifications": {
        "enabled": True,
        "cooldown": 60,
        "urls": [],
    },
    "ups_devices": {},
}


def load_config() -> Dict[str, Any]:
    config_file_exists = os.path.exists(CONFIG_PATH)
    loaded = None
    
    if config_file_exists:
        try:
            with open(CONFIG_PATH, "r") as f:
                loaded = _yaml.load(f)
        except Exception:
            loaded = None

    if not isinstance(loaded, dict):
        loaded = None

    config = copy.deepcopy(DEFAULT_CONFIG)
    migrated_from_old_format = False
    
    if loaded:
        if "ups_devices" not in loaded:
            migrated_from_old_format = True
            if "nut_server" in loaded:
                config["nut_server"] = _deep_to_dict(loaded["nut_server"])
            if "notifications" in loaded:
                config["notifications"] = _deep_to_dict(loaded["notifications"])
            if "check_interval" in loaded and "check_interval" not in config["nut_server"]:
                config["nut_server"]["check_interval"] = loaded["check_interval"]

            old_settings = copy.deepcopy(DEFAULT_UPS_CONFIG)
            if "alert_mode" in loaded:
                old_settings["alert_mode"] = loaded["alert_mode"]
            if "basic_alerts" in loaded:
                old_settings["basic_alerts"] = _deep_to_dict(loaded["basic_alerts"])
            if "formula_alert" in loaded:
                old_settings["formula_alert"] = _deep_to_dict(loaded["formula_alert"])

            ups_names = fetch_nut_ups_names(config["nut_server"]["host"], config["nut_server"]["port"])
            if ups_names:
                for ups_name in ups_names:
                    config["ups_devices"][ups_name] = copy.deepcopy(old_settings)
        else:
            for k, v in loaded.items():
                if k == "ups_devices":
                    continue
                config[k] = _deep_to_dict(v) if isinstance(v, dict) else v
            if isinstance(loaded.get("ups_devices"), dict):
                config["ups_devices"] = _deep_to_dict(loaded["ups_devices"])

    if "ups_devices" not in config or not isinstance(config["ups_devices"], dict):
        config["ups_devices"] = {}

    ups_names = fetch_nut_ups_names(config["nut_server"]["host"], config["nut_server"]["port"])
    new_devices = []
    if ups_names:
        for ups_name in ups_names:
            if ups_name not in config["ups_devices"]:
                config["ups_devices"][ups_name] = copy.deepcopy(DEFAULT_UPS_CONFIG)
                new_devices.append(ups_name)

        config["ups_devices"] = {
            name: cfg for name, cfg in config["ups_devices"].items()
            if name in ups_names
        }

    if new_devices or migrated_from_old_format or not config_file_exists:
        _save_with_new_devices(loaded, new_devices, config_file_exists, migrated_from_old_format)

    return config


DEFAULT_CONFIG_TEMPLATE = """# nutalert configuration
# ups devices are auto-discovered from the nut server on first run

nut_server:
  host: 127.0.0.1
  port: 3493
  check_interval: 15

notifications:
  enabled: false
  cooldown: 60
  urls: []
  # apprise urls - see https://github.com/caronc/apprise
  # - tgram://bot_token/chat_id
  # - discord://webhook_id/webhook_token
  # - slack://token_a/token_b/token_c

# ups devices will be auto-populated here after connecting to your nut server
ups_devices: {}
"""


def _extract_old_urls(loaded: dict) -> list:
    if not loaded:
        return []
    notifications = loaded.get("notifications", {})
    if not isinstance(notifications, dict):
        return []
    urls = notifications.get("urls", [])
    if isinstance(urls, list):
        return [u for u in urls if u]
    return []


def _save_with_new_devices(loaded, new_devices: list, config_file_exists: bool, migrated_from_old_format: bool = False):
    if config_file_exists and loaded is not None:
        was_old_format = "ups_devices" not in loaded
        if was_old_format:
            logger.info("migrating config from v1.x to v2.x format")
            old_urls = _extract_old_urls(loaded)
            config = copy.deepcopy(DEFAULT_CONFIG)
            if old_urls:
                config["notifications"]["urls"] = old_urls
                logger.info(f"migrated {len(old_urls)} notification url(s)")
            if "nut_server" in loaded:
                ns = loaded["nut_server"]
                if isinstance(ns, dict):
                    if "host" in ns:
                        config["nut_server"]["host"] = ns["host"]
                    if "port" in ns:
                        config["nut_server"]["port"] = ns["port"]
                    if "check_interval" in ns:
                        config["nut_server"]["check_interval"] = ns["check_interval"]
            if "check_interval" in loaded:
                config["nut_server"]["check_interval"] = loaded["check_interval"]
            if "notifications" in loaded:
                notif = loaded["notifications"]
                if isinstance(notif, dict):
                    if "enabled" in notif:
                        config["notifications"]["enabled"] = notif["enabled"]
                    if "cooldown" in notif:
                        config["notifications"]["cooldown"] = notif["cooldown"]
            old_settings = copy.deepcopy(DEFAULT_UPS_CONFIG)
            if "alert_mode" in loaded:
                old_settings["alert_mode"] = loaded["alert_mode"]
            if "basic_alerts" in loaded:
                old_settings["basic_alerts"] = _deep_to_dict(loaded["basic_alerts"])
            if "formula_alert" in loaded:
                old_settings["formula_alert"] = _deep_to_dict(loaded["formula_alert"])
            host = config["nut_server"]["host"]
            port = config["nut_server"]["port"]
            ups_names = fetch_nut_ups_names(host, port)
            if ups_names:
                for ups_name in ups_names:
                    config["ups_devices"][ups_name] = copy.deepcopy(old_settings)
                    logger.info(f"migrated settings for ups '{ups_name}'")
            try:
                with open(CONFIG_PATH, "w") as f:
                    _yaml.dump(config, f)
                logger.info("config migration completed successfully")
            except Exception as e:
                logger.error(f"failed to save config: {e}")
            return
                    
        for ups_name in new_devices:
            if ups_name not in loaded.get("ups_devices", {}):
                if "ups_devices" not in loaded:
                    loaded["ups_devices"] = {}
                loaded["ups_devices"][ups_name] = copy.deepcopy(DEFAULT_UPS_CONFIG)
                logger.info(f"discovered new ups device '{ups_name}'")
        
        try:
            with open(CONFIG_PATH, "w") as f:
                _yaml.dump(loaded, f)
            if new_devices:
                logger.info(f"config updated with {len(new_devices)} new device(s)")
        except Exception as e:
            logger.error(f"failed to save config: {e}")
    else:
        try:
            with open(CONFIG_PATH, "w") as f:
                f.write(DEFAULT_CONFIG_TEMPLATE)
            logger.info("created new config file")
        except Exception as e:
            logger.error(f"failed to create config: {e}")


def _deep_to_dict(obj):
    if hasattr(obj, "items"):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_to_dict(item) for item in obj]
    return obj


def save_config(config: Dict[str, Any]) -> str:
    try:
        with open(CONFIG_PATH, "w") as f:
            _yaml.dump(config, f)
        return "config saved successfully."
    except Exception as e:
        return f"failed to save config: {e}"


def save_config_text(yaml_text: str) -> str:
    try:
        _yaml.load(StringIO(yaml_text))
        with open(CONFIG_PATH, "w") as f:
            f.write(yaml_text)
        return "config saved successfully."
    except Exception as e:
        return f"failed to save config: {e}"


def load_config_text() -> str:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return f.read()
    return ""
