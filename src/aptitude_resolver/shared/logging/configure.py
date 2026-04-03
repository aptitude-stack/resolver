"""Logging bootstrap helpers for the Aptitude Resolver."""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: int | str = logging.INFO) -> structlog.stdlib.BoundLogger:
    """Configure process-wide structured logging for the client."""

    logging.basicConfig(level=level, format="%(message)s", force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.getLogger("aptitude_resolver").setLevel(level)
    return structlog.stdlib.get_logger("aptitude_resolver")
