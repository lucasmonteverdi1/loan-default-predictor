"""JSON logging configuration compatible with Google Cloud Logging.

Cloud Run auto-parses JSON lines written to stdout. For Cloud Logging to
pick up the severity level and timestamp correctly, the payload needs
`severity` (mapped from Python's `levelname`) and an ISO `timestamp`
field — see https://cloud.google.com/logging/docs/structured-logging.

Locally this behaves identically to any JSON logger: pretty useless in
a terminal, but the structure makes it queryable in Cloud Logging.
"""

from __future__ import annotations

import logging
import logging.config
from datetime import datetime, timezone

from pythonjsonlogger import jsonlogger


class CloudLoggingFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that adds `severity` and a UTC `timestamp` field."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["severity"] = record.levelname
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()


def build_logging_config(level: str) -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "app.logging_config.CloudLoggingFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
            }
        },
        "root": {"handlers": ["stdout"], "level": level.upper()},
    }


def configure_logging(level: str) -> None:
    logging.config.dictConfig(build_logging_config(level))
