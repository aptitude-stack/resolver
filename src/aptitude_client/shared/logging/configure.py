"""Logging bootstrap helpers for the Aptitude client."""

from __future__ import annotations

import logging
from typing import Union


DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: Union[int, str] = logging.INFO) -> logging.Logger:
    """Configure process-wide logging for the client and return its root logger."""

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
    else:
        root_logger.setLevel(level)

    logger = logging.getLogger("aptitude_client")
    logger.setLevel(level)
    return logger
