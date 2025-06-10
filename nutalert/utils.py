# ==============================================================================
# File: nutalert/utils.py
# (This version correctly finds the config file in the parent directory)
# ==============================================================================
import os
import sys
import yaml
import logging
from collections import deque

LOG_BUFFER = deque(maxlen=100)


class LogBufferIO:
    def write(self, message):
        if message.strip():
            LOG_BUFFER.append(message.strip())

    def flush(self):
        pass


def setup_logger(name=__name__, level=logging.INFO):
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    log_buffer_handler = logging.StreamHandler(LogBufferIO())
    log_buffer_handler.setFormatter(formatter)
    logger.addHandler(log_buffer_handler)
    return logger


def get_recent_logs():
    return "\n".join(LOG_BUFFER)


def get_config_path():
    """
    CHANGED: This function is now robust. It finds the config.yaml file
    in the project's root directory (parent of the script's directory).
    """
    # Get the directory where this utils.py script is located.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory (the project root).
    project_root = os.path.dirname(script_dir)

    # Construct the path to config.yaml in the project root.
    return os.path.join(project_root, 'config.yaml')


def load_config():
    path = get_config_path()
    if not os.path.exists(path):
        logging.getLogger(__name__).warning(f"Config file not found at '{path}'. Creating a default one.")
        default_config = {
            'nut_server': {'host': '127.0.0.1', 'port': 3493, 'timeout': 5},
            'check_interval': 15,
            'alert_mode': 'basic',
            'basic_alerts': {'battery_charge': {'enabled': False, 'min': 20}}
        }
        save_config(default_config)
        return default_config
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logging.getLogger(__name__).error(f"Error parsing config file '{path}': {e}")
        return {}


def save_config(config_data):
    path = get_config_path()
    try:
        with open(path, "w") as f:
            yaml.dump(config_data, f, sort_keys=False, indent=2)
        return "✅ Configuration saved successfully!"
    except Exception as e:
        error_msg = f"Error saving configuration: {e}"
        logging.getLogger(__name__).error(error_msg)
        return f"❌ {error_msg}"