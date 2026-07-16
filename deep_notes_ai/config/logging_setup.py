"""
deep_notes_ai/config/logging_setup.py

Configures a logger with optional console output and file logging.

Supports:
- Human-readable or JSON logs
- Optional console logging
- Configurable logger name
- File logging to a configurable directory
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger


def configure_logging(
    logger_name: str,
    log_level: str,
    structured: bool,
    log_dir: Path,
    *,
    enable_console: bool = False,
    log_filename: str = "pipeline.log",
) -> Path:
    """
    Configure a logger.

    Args:
        logger_name:
            Name of the logger (e.g. "deep_notes_ai").

        log_level:
            Logging level ("INFO", "DEBUG", etc.).

        structured:
            If True, emits JSON logs.
            Otherwise emits human-readable logs.

        log_dir:
            Directory where the log file will be created.

        enable_console:
            Whether to also log to stdout.

        log_filename:
            Name of the log file.

    Returns:
        Path to the created log file.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / log_filename

    if structured:
        formatter = jsonlogger.JsonFormatter(
            fmt=(
                "%(asctime)s "
                "%(levelname)s "
                "%(name)s "
                "%(module)s "
                "%(funcName)s "
                "%(lineno)d "
                "%(message)s"
            ),
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
            },
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handlers: list[logging.Handler] = []

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    file_handler = logging.FileHandler(
        filename=log_file_path,
        mode="w",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)

    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()

    for handler in handlers:
        logger.addHandler(handler)

    logger.propagate = False

    return log_file_path