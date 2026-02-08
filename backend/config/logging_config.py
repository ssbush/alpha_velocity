"""
Logging Configuration for AlphaVelocity

Provides centralized logging configuration with structured logging,
log rotation, and environment-specific settings.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import json


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging

    Outputs log records as JSON for easy parsing and aggregation
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'ticker'):
            log_data['ticker'] = record.ticker
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for better readability during development
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format: [TIMESTAMP] LEVEL - MODULE.FUNCTION:LINE - MESSAGE
        formatted = (
            f"{color}[{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}] "
            f"{record.levelname:8s}{reset} - "
            f"{record.module}.{record.funcName}:{record.lineno} - "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    json_logs: bool = False,
    console_output: bool = True
) -> None:
    """
    Setup logging configuration for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (creates if doesn't exist)
        json_logs: Use JSON formatting (recommended for production)
        console_output: Enable console output (recommended for development)
    """

    # Get log level from environment or parameter
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level.upper())

    # Get log directory
    if log_dir is None:
        log_dir = os.getenv('LOG_DIR', 'logs')

    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler (for development)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if json_logs:
            console_formatter = JSONFormatter()
        else:
            console_formatter = ColoredFormatter()

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation (for all logs)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / 'alphavelocity.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)

    if json_logs:
        file_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s - %(name)s.%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Error file handler (only errors and critical)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / 'errors.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized - Level: {logging.getLevelName(log_level)}, "
        f"Directory: {log_path}, JSON: {json_logs}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Performance logging helper
class PerformanceLogger:
    """Context manager for performance logging"""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.debug(f"Starting: {self.operation}", extra=self.extra)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        self.extra['duration_ms'] = round(duration, 2)

        if exc_type is None:
            if duration > 1000:  # Slow operation (> 1 second)
                self.logger.warning(
                    f"Slow operation: {self.operation} took {duration:.2f}ms",
                    extra=self.extra
                )
            else:
                self.logger.debug(
                    f"Completed: {self.operation} in {duration:.2f}ms",
                    extra=self.extra
                )
        else:
            self.logger.error(
                f"Failed: {self.operation} after {duration:.2f}ms - {exc_val}",
                extra=self.extra,
                exc_info=(exc_type, exc_val, exc_tb)
            )
