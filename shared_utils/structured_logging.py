"""
Structured logging with JSON support for enterprise deployments
Provides consistent, parseable logging across the application
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import traceback


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging

    Outputs logs in JSON format for easy parsing by log aggregators
    like Elasticsearch, Splunk, or CloudWatch
    """

    def __init__(
        self,
        fmt_keys: Optional[Dict[str, str]] = None,
        include_trace: bool = True,
    ):
        """
        Initialize JSON formatter

        Args:
            fmt_keys: Dictionary mapping format keys to log record attributes
            include_trace: Whether to include stack traces for exceptions
        """
        super().__init__()
        self.fmt_keys = fmt_keys or {
            "timestamp": "asctime",
            "level": "levelname",
            "logger": "name",
            "message": "message",
        }
        self.include_trace = include_trace

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base message
        message = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "function"):
            message["function"] = record.funcName
        if hasattr(record, "lineno"):
            message["line"] = record.lineno
        if hasattr(record, "pathname"):
            message["file"] = Path(record.pathname).name

        # Add process/thread info
        if hasattr(record, "process"):
            message["process"] = record.process
        if hasattr(record, "thread"):
            message["thread"] = record.thread

        # Add exception info if present
        if record.exc_info and self.include_trace:
            message["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add custom fields from extra parameter
        if hasattr(record, "extra_fields"):
            message.update(record.extra_fields)

        return json.dumps(message, default=str)

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """
        Format timestamp in ISO 8601 format

        Args:
            record: Log record
            datefmt: Date format string (ignored, always uses ISO 8601)

        Returns:
            ISO 8601 formatted timestamp
        """
        return datetime.fromtimestamp(record.created).isoformat()


class ColoredTextFormatter(logging.Formatter):
    """
    Colored console formatter for human-readable logs

    Uses ANSI color codes for better readability in terminal
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors

        Args:
            record: Log record to format

        Returns:
            Colored log string
        """
        # Get color for level
        color = self.COLORS.get(record.levelname, "")

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Build message
        log_message = (
            f"{color}{self.BOLD}[{record.levelname}]{self.RESET} "
            f"{timestamp} - {record.name} - "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            log_message += "\n" + self.formatException(record.exc_info)

        return log_message


class StructuredLogger:
    """
    Factory for creating structured loggers with consistent configuration
    """

    @staticmethod
    def get_logger(
        name: str,
        level: str = "INFO",
        log_format: str = "json",
        log_file: Optional[Path] = None,
    ) -> logging.Logger:
        """
        Get or create a structured logger

        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Format type ("json" or "text")
            log_file: Optional file path for file logging

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)

        # Avoid duplicate handlers
        if logger.handlers:
            return logger

        logger.setLevel(getattr(logging, level.upper()))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))

        if log_format.lower() == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ColoredTextFormatter())

        logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.upper()))
            # Always use JSON for file logs
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)

        return logger


class LogContext:
    """
    Context manager for adding extra fields to logs

    Usage:
        with LogContext(logger, user_id="123", request_id="abc"):
            logger.info("Processing request")
    """

    def __init__(self, logger: logging.Logger, **extra_fields):
        """
        Initialize log context

        Args:
            logger: Logger to add context to
            **extra_fields: Additional fields to include in logs
        """
        self.logger = logger
        self.extra_fields = extra_fields
        self.old_factory = None

    def __enter__(self):
        """Enter context - add extra fields"""
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.extra_fields = self.extra_fields
            return record

        logging.setLogRecordFactory(record_factory)
        self.old_factory = old_factory
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original factory"""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


# Convenience function
def setup_structured_logging(
    app_name: str = "comfyui-3d-pack",
    level: str = "INFO",
    log_format: str = "json",
    log_dir: Optional[Path] = None,
) -> logging.Logger:
    """
    Set up structured logging for the application

    Args:
        app_name: Application name for logger
        level: Log level
        log_format: Format type ("json" or "text")
        log_dir: Optional directory for log files

    Returns:
        Configured root logger
    """
    log_file = None
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{app_name}.log"

    return StructuredLogger.get_logger(
        app_name,
        level=level,
        log_format=log_format,
        log_file=log_file,
    )


# Example usage
if __name__ == "__main__":
    # JSON logging
    logger = setup_structured_logging(log_format="json", level="DEBUG")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")

    # With context
    with LogContext(logger, request_id="req-123", user_id="user-456"):
        logger.info("Processing user request")

    # With exception
    try:
        1 / 0
    except Exception as e:
        logger.error("An error occurred", exc_info=True)

    print("\n" + "=" * 50 + "\n")

    # Text logging
    logger_text = setup_structured_logging(log_format="text", level="DEBUG")
    logger_text.debug("Debug message")
    logger_text.info("Info message")
    logger_text.warning("Warning message")
