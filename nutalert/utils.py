import os
import sys
import yaml
import logging


def setup_logger(name=__name__, level=logging.DEBUG):
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    return logger


def load_config(config_path=None):
    path = config_path or os.environ.get("CONFIG_PATH") or "/config/config.yaml"

    if not os.path.exists(path):
        path = "config.yaml"

    with open(path, "r") as f:
        return yaml.safe_load(f)
