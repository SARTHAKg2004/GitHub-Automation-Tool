"""
modules/logger.py
Centralised logging — scanLogs.log + errorLogs.log
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setupLogger(name: str = "githubValidator") -> logging.Logger:
    """Create and return the root application logger."""
    logDir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logDir, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:          # already configured
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── scan log (INFO+) ───────────────────────────────────────────────────
    scanHandler = RotatingFileHandler(
        os.path.join(logDir, "scanLogs.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    scanHandler.setLevel(logging.INFO)
    scanHandler.setFormatter(fmt)

    # ── error log (ERROR+) ─────────────────────────────────────────────────
    errorHandler = RotatingFileHandler(
        os.path.join(logDir, "errorLogs.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    errorHandler.setLevel(logging.ERROR)
    errorHandler.setFormatter(fmt)

    # ── console (INFO+) ────────────────────────────────────────────────────
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.INFO)
    consoleHandler.setFormatter(fmt)

    logger.addHandler(scanHandler)
    logger.addHandler(errorHandler)
    logger.addHandler(consoleHandler)

    return logger


def getLogger(name: str = "githubValidator") -> logging.Logger:
    return logging.getLogger(name)
