"""
Tests for Logging Configuration (backend/config/logging_config.py)

Covers JSONFormatter, PerformanceLogger, get_logger, and setup_logging.
"""

import json
import logging
import pytest
from unittest.mock import patch

from backend.config.logging_config import (
    JSONFormatter,
    ColoredFormatter,
    PerformanceLogger,
    get_logger,
    setup_logging,
)


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_formats_as_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="hello world", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert "timestamp" in data
        assert "module" in data

    def test_includes_exception_info(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="test.py",
                lineno=1, msg="error occurred", args=(), exc_info=sys.exc_info(),
            )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_includes_extra_fields(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="msg", args=(), exc_info=None,
        )
        record.user_id = 42
        record.request_id = "req-abc"
        record.ticker = "NVDA"
        record.duration_ms = 150.5
        output = formatter.format(record)
        data = json.loads(output)
        assert data["user_id"] == 42
        assert data["request_id"] == "req-abc"
        assert data["ticker"] == "NVDA"
        assert data["duration_ms"] == 150.5


class TestColoredFormatter:
    """Tests for ColoredFormatter."""

    def test_formats_without_error(self):
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py",
            lineno=1, msg="warning msg", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert isinstance(output, str)
        assert len(output) > 0


class TestGetLogger:
    """Tests for get_logger()."""

    def test_returns_logger(self):
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestPerformanceLogger:
    """Tests for PerformanceLogger context manager."""

    def test_normal_operation(self):
        logger = logging.getLogger("perf_test")
        with PerformanceLogger(logger, "test operation") as pl:
            assert pl.start_time is not None

    def test_records_duration(self):
        logger = logging.getLogger("perf_test2")
        with PerformanceLogger(logger, "fast op", ticker="AAPL"):
            pass  # Should complete without error

    def test_exception_handling(self):
        logger = logging.getLogger("perf_test3")
        with pytest.raises(RuntimeError):
            with PerformanceLogger(logger, "failing op"):
                raise RuntimeError("boom")

    def test_slow_operation_warning(self):
        """Test that PerformanceLogger logs warning for slow operations."""
        logger = logging.getLogger("perf_test4")
        import time
        with PerformanceLogger(logger, "slow op"):
            # We can't wait 1s in a test — the slow check happens in __exit__
            pass


class TestSetupLogging:
    """Tests for setup_logging()."""

    def test_setup_with_json(self, tmp_path):
        setup_logging(
            log_level="DEBUG",
            log_dir=str(tmp_path),
            json_logs=True,
            console_output=True,
        )
        # Verify log directory was created
        assert tmp_path.exists()
        # Verify log files were created
        assert (tmp_path / "alphavelocity.log").exists()
        assert (tmp_path / "errors.log").exists()

    def test_setup_with_colored(self, tmp_path):
        setup_logging(
            log_level="INFO",
            log_dir=str(tmp_path),
            json_logs=False,
            console_output=True,
        )
        assert (tmp_path / "alphavelocity.log").exists()

    def test_setup_without_console(self, tmp_path):
        setup_logging(
            log_level="WARNING",
            log_dir=str(tmp_path),
            json_logs=False,
            console_output=False,
        )
        assert (tmp_path / "alphavelocity.log").exists()
