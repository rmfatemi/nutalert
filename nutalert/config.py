import os
import yaml
import copy
from typing import Dict, Any

from nutalert.fetcher import fetch_nut_ups_names


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))


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
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_file_exists = os.path.exists(CONFIG_PATH)
    if config_file_exists:
        try:
            with open(CONFIG_PATH, "r") as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    if k == "ups_devices" and isinstance(v, dict):
                        continue
                    config[k] = v
                if "ups_devices" in loaded and isinstance(loaded["ups_devices"], dict):
                    config["ups_devices"] = copy.deepcopy(loaded["ups_devices"])
        except Exception:
            pass  # Ignore errors, fall back to defaults
    # Always ensure ups_devices is a dict
    if "ups_devices" not in config or not isinstance(config["ups_devices"], dict):
        config["ups_devices"] = {}
    # Discover UPS devices
    ups_names = fetch_nut_ups_names(config["nut_server"]["host"], config["nut_server"]["port"])
    changed = False
    if ups_names:
        for ups_name in ups_names:
            if ups_name not in config["ups_devices"]:
                config["ups_devices"][ups_name] = copy.deepcopy(DEFAULT_UPS_CONFIG)
                changed = True
    # Do NOT remove missing devices, and do NOT clear ups_devices if none found
    if changed or not config_file_exists:
        save_config(config)
    return config


def save_config(config: Dict[str, Any]) -> str:
    class NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    try:
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, sort_keys=False, Dumper=NoAliasDumper)
        return "config saved successfully."
    except Exception as e:
        return f"failed to save config: {e}"
