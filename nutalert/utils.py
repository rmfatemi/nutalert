import sys
import logging

from collections import deque


LOG_BUFFER: deque[str] = deque(maxlen=100)


class LogBufferIO:
    def write(self, message: str) -> None:
        if message.strip():
            LOG_BUFFER.append(message.strip())

    def flush(self) -> None:
        pass


def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
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


def get_recent_logs() -> str:
    return "\n".join(LOG_BUFFER)
