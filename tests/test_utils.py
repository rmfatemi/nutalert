import pytest

from nutalert.utils import setup_logger, get_recent_logs, LOG_BUFFER


class TestSetupLogger:
    def test_logger_creation(self):
        logger = setup_logger("test_logger")
        
        assert logger is not None
        assert logger.name == "test_logger"
        assert len(logger.handlers) >= 1

    def test_logger_with_custom_level(self):
        import logging
        
        logger = setup_logger("test_logger_debug", level=logging.DEBUG)
        
        assert logger.level == logging.DEBUG

    def test_logger_clears_existing_handlers(self):
        logger1 = setup_logger("test_logger_clear")
        initial_handlers = len(logger1.handlers)
        
        logger2 = setup_logger("test_logger_clear")
        
        assert len(logger2.handlers) == initial_handlers


class TestLogBuffer:
    def test_log_buffer_captures_logs(self):
        LOG_BUFFER.clear()
        
        logger = setup_logger("test_buffer_logger")
        logger.info("Test message")
        
        logs = get_recent_logs()
        assert "Test message" in logs

    def test_log_buffer_max_lines(self):
        LOG_BUFFER.clear()
        
        logger = setup_logger("test_max_logger")
        for i in range(150):
            logger.info(f"Message {i}")
        
        logs = get_recent_logs()
        lines = logs.strip().split("\n")
        
        assert len(lines) <= 100

    def test_get_recent_logs_returns_string(self):
        result = get_recent_logs()
        
        assert isinstance(result, str)
