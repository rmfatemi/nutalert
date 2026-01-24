import os
import copy
import shutil

from io import StringIO
from typing import Dict, Any
from datetime import datetime

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from nutalert.fetcher import fetch_nut_ups_names
from nutalert.utils import setup_logger


logger = setup_logger("config")

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml")))

CURRENT_CONFIG_VERSION = 2

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
    "config_version": CURRENT_CONFIG_VERSION,
    "nut_server": {
        "host": "127.0.0.1",
        "port": 3493,
        "check_interval": 15,
    },
    "notifications": {
        "enabled": True,
        "cooldown": 60,
        "urls": "",
    },
    "ups_devices": {},
}


def _is_old_format(loaded: Dict[str, Any]) -> bool:
    if loaded.get("config_version"):
        return False
    has_top_level_alerts = any(k in loaded for k in ["basic_alerts", "formula_alert", "alert_mode"])
    has_no_ups_devices = "ups_devices" not in loaded or not loaded.get("ups_devices")
    return has_top_level_alerts or has_no_ups_devices


def _backup_config() -> str | None:
    if not os.path.exists(CONFIG_PATH):
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{CONFIG_PATH}.{timestamp}.bak"
    try:
        shutil.copy2(CONFIG_PATH, backup_path)
        logger.info(f"config backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"failed to create config backup: {e}")
        return None


def _migrate_v1_to_v2(old_config: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("migrating config from v1 to v2 format...")
    
    new_config = copy.deepcopy(DEFAULT_CONFIG)
    new_config["config_version"] = CURRENT_CONFIG_VERSION
    
    if "nut_server" in old_config:
        new_config["nut_server"] = old_config["nut_server"].copy()
        if "check_interval" not in new_config["nut_server"] and "check_interval" in old_config:
            new_config["nut_server"]["check_interval"] = old_config["check_interval"]
    elif "check_interval" in old_config:
        new_config["nut_server"]["check_interval"] = old_config["check_interval"]
    
    if "notifications" in old_config:
        new_config["notifications"] = old_config["notifications"].copy()
    
    device_config = copy.deepcopy(DEFAULT_UPS_CONFIG)
    
    if "alert_mode" in old_config:
        device_config["alert_mode"] = old_config["alert_mode"]
    
    if "basic_alerts" in old_config:
        device_config["basic_alerts"] = old_config["basic_alerts"].copy()
    
    if "formula_alert" in old_config:
        device_config["formula_alert"] = old_config["formula_alert"].copy()
    
    new_config["_migrated_device_config"] = device_config
    
    logger.info("config migration completed")
    return new_config


def _build_commented_config(config: Dict[str, Any]) -> CommentedMap:
    cm = CommentedMap()
    
    cm.yaml_set_start_comment(
        "NutAlert Configuration\n"
        "======================\n"
        "UPS devices are auto-discovered from your NUT server.\n"
        "Edit values below and save to apply changes.\n"
    )
    
    cm["config_version"] = config.get("config_version", CURRENT_CONFIG_VERSION)
    cm.yaml_add_eol_comment("Do not modify - used for migration", "config_version")
    
    nut = CommentedMap()
    nut_cfg = config.get("nut_server", DEFAULT_CONFIG["nut_server"])
    nut["host"] = nut_cfg.get("host", "127.0.0.1")
    nut["port"] = nut_cfg.get("port", 3493)
    nut["check_interval"] = nut_cfg.get("check_interval", 15)
    nut.yaml_add_eol_comment("NUT server hostname or IP", "host")
    nut.yaml_add_eol_comment("NUT server port", "port")
    nut.yaml_add_eol_comment("Polling interval in seconds", "check_interval")
    cm["nut_server"] = nut
    
    notif = CommentedMap()
    notif_cfg = config.get("notifications", DEFAULT_CONFIG["notifications"])
    notif["enabled"] = notif_cfg.get("enabled", True)
    notif["cooldown"] = notif_cfg.get("cooldown", 60)
    notif.yaml_add_eol_comment("Enable/disable all notifications", "enabled")
    notif.yaml_add_eol_comment("Minimum seconds between repeated alerts", "cooldown")
    
    urls_cfg = notif_cfg.get("urls", "")
    
    if isinstance(urls_cfg, list):
        url_lines = []
        for item in urls_cfg:
            if isinstance(item, str) and item:
                url_lines.append(item)
            elif isinstance(item, dict):
                url = item.get("url", "")
                if url and item.get("enabled", True):
                    url_lines.append(url)
        urls_str = "\n".join(url_lines) + "\n" if url_lines else ""
    else:
        urls_str = str(urls_cfg) if urls_cfg else ""
    
    from ruamel.yaml.scalarstring import LiteralScalarString
    notif["urls"] = LiteralScalarString(urls_str) if urls_str else ""
    notif.yaml_add_eol_comment("Apprise URLs, one per line - see https://github.com/caronc/apprise", "urls")
    
    cm["notifications"] = notif
    
    devices = CommentedMap()
    devices_cfg = config.get("ups_devices", {})
    
    if not devices_cfg:
        devices.yaml_set_start_comment(
            "UPS devices will be auto-discovered from your NUT server.\n"
            "Once discovered, customize per-device settings here."
        )
    
    for device_name, device_cfg in devices_cfg.items():
        dev = _build_commented_device_config(device_cfg)
        devices[device_name] = dev
    
    cm["ups_devices"] = devices
    
    return cm


def _build_commented_device_config(device_cfg: Dict[str, Any]) -> CommentedMap:
    dev = CommentedMap()
    cfg = {**DEFAULT_UPS_CONFIG, **device_cfg}
    
    dev["alert_mode"] = cfg.get("alert_mode", "basic")
    dev.yaml_add_eol_comment('"basic" for thresholds, "formula" for custom logic', "alert_mode")
    
    gs = CommentedMap()
    gs_cfg = cfg.get("gauge_settings", DEFAULT_UPS_CONFIG["gauge_settings"])
    
    load = CommentedMap()
    load_cfg = gs_cfg.get("load", {})
    load["warn_threshold"] = load_cfg.get("warn_threshold", 80)
    load["high_threshold"] = load_cfg.get("high_threshold", 100)
    load.yaml_add_eol_comment("Yellow above this %", "warn_threshold")
    load.yaml_add_eol_comment("Red above this %", "high_threshold")
    gs["load"] = load
    
    charge = CommentedMap()
    charge_cfg = gs_cfg.get("charge_remaining", {})
    charge["warn_threshold"] = charge_cfg.get("warn_threshold", 35)
    charge["high_threshold"] = charge_cfg.get("high_threshold", 15)
    charge.yaml_add_eol_comment("Yellow below this %", "warn_threshold")
    charge.yaml_add_eol_comment("Red below this %", "high_threshold")
    gs["charge_remaining"] = charge
    
    runtime = CommentedMap()
    runtime_cfg = gs_cfg.get("runtime", {})
    runtime["warn_threshold"] = runtime_cfg.get("warn_threshold", 15)
    runtime["high_threshold"] = runtime_cfg.get("high_threshold", 5)
    runtime.yaml_add_eol_comment("Yellow below this (minutes)", "warn_threshold")
    runtime.yaml_add_eol_comment("Red below this (minutes)", "high_threshold")
    gs["runtime"] = runtime
    
    voltage = CommentedMap()
    voltage_cfg = gs_cfg.get("voltage", {})
    voltage["nominal"] = voltage_cfg.get("nominal", 120)
    voltage["warn_deviation"] = voltage_cfg.get("warn_deviation", 10)
    voltage["high_deviation"] = voltage_cfg.get("high_deviation", 15)
    voltage.yaml_add_eol_comment("Expected voltage (230 for EU)", "nominal")
    voltage.yaml_add_eol_comment("% deviation for yellow", "warn_deviation")
    voltage.yaml_add_eol_comment("% deviation for red", "high_deviation")
    gs["voltage"] = voltage
    
    dev["gauge_settings"] = gs
    
    ba = CommentedMap()
    ba_cfg = cfg.get("basic_alerts", DEFAULT_UPS_CONFIG["basic_alerts"])
    
    for alert_name in ["battery_charge", "runtime", "load", "input_voltage", "ups_status"]:
        alert = CommentedMap()
        alert_cfg = ba_cfg.get(alert_name, DEFAULT_UPS_CONFIG["basic_alerts"].get(alert_name, {}))
        
        alert["enabled"] = alert_cfg.get("enabled", True)
        
        if "min" in alert_cfg:
            alert["min"] = alert_cfg["min"]
        if "max" in alert_cfg:
            alert["max"] = alert_cfg["max"]
        if "acceptable" in alert_cfg:
            alert["acceptable"] = alert_cfg["acceptable"]
        if "alert_when_status_changed" in alert_cfg:
            alert["alert_when_status_changed"] = alert_cfg["alert_when_status_changed"]
        
        alert["message"] = alert_cfg.get("message", DEFAULT_UPS_CONFIG["basic_alerts"].get(alert_name, {}).get("message", ""))
        
        ba[alert_name] = alert
    
    dev["basic_alerts"] = ba
    
    fa = CommentedMap()
    fa_cfg = cfg.get("formula_alert", DEFAULT_UPS_CONFIG["formula_alert"])
    fa["expression"] = fa_cfg.get("expression", DEFAULT_UPS_CONFIG["formula_alert"]["expression"])
    fa["message"] = fa_cfg.get("message", DEFAULT_UPS_CONFIG["formula_alert"]["message"])
    fa.yaml_add_eol_comment("Variables: ups_load, battery_charge, actual_runtime_minutes, battery_voltage, input_voltage, ups_status", "expression")
    dev["formula_alert"] = fa
    
    return dev


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

    migrated_device_config = None
    if loaded and _is_old_format(loaded):
        _backup_config()
        loaded = _migrate_v1_to_v2(loaded)
        migrated_device_config = loaded.pop("_migrated_device_config", None)
        logger.info("old config format detected and migrated")

    config = copy.deepcopy(DEFAULT_CONFIG)
    
    if loaded:
        for k, v in loaded.items():
            if k == "ups_devices":
                continue
            config[k] = _deep_to_dict(v) if isinstance(v, dict) else v
        if isinstance(loaded.get("ups_devices"), dict):
            config["ups_devices"] = _deep_to_dict(loaded["ups_devices"])

    if "ups_devices" not in config or not isinstance(config["ups_devices"], dict):
        config["ups_devices"] = {}

    config["config_version"] = config.get("config_version", CURRENT_CONFIG_VERSION)

    ups_names = fetch_nut_ups_names(config["nut_server"]["host"], config["nut_server"]["port"])
    new_devices = []
    if ups_names:
        for ups_name in ups_names:
            if ups_name not in config["ups_devices"]:
                if migrated_device_config:
                    config["ups_devices"][ups_name] = copy.deepcopy(migrated_device_config)
                else:
                    config["ups_devices"][ups_name] = copy.deepcopy(DEFAULT_UPS_CONFIG)
                new_devices.append(ups_name)
                logger.info(f"discovered new ups device '{ups_name}'")

        for name in list(config["ups_devices"].keys()):
            if name not in ups_names:
                logger.warning(f"ups device '{name}' not found on server (keeping in config)")

    if new_devices or not config_file_exists or migrated_device_config:
        _save_config_file(config)
        if not config_file_exists:
            logger.info("created new config file")
        elif migrated_device_config:
            logger.info("saved migrated config file")

    return config


def _save_config_file(config: Dict[str, Any]):
    try:
        commented_config = _build_commented_config(config)
        with open(CONFIG_PATH, "w") as f:
            _yaml.dump(commented_config, f)
    except Exception as e:
        logger.error(f"failed to save config: {e}")


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
