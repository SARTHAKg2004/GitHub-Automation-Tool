"""
modules/fileClassifier.py
Classifies files into Frontend / Backend / Config / Binary / Unknown.
"""

import os
from modules.config import Config


def classifyFile(filePath: str) -> str:
    """
    Returns one of: Frontend | Backend | Config | Binary | Unknown
    """
    _, ext = os.path.splitext(filePath.lower())

    if ext in Config.BINARY_EXTENSIONS:
        return "Binary"
    if ext in Config.FRONTEND_EXTENSIONS:
        return "Frontend"
    if ext in Config.BACKEND_EXTENSIONS:
        return "Backend"
    if ext in Config.CONFIG_EXTENSIONS:
        return "Config"

    # Heuristic: no extension → try filename
    basename = os.path.basename(filePath).lower()
    noExtNames = {
        "dockerfile": "Config",
        "makefile": "Config",
        "jenkinsfile": "Config",
        "vagrantfile": "Config",
        "gemfile": "Config",
        "procfile": "Config",
        "rakefile": "Backend",
    }
    return noExtNames.get(basename, "Unknown")


def isBinaryFile(filePath: str) -> bool:
    """Quick check: is this a known binary extension?"""
    _, ext = os.path.splitext(filePath.lower())
    return ext in Config.BINARY_EXTENSIONS


def isTextReadable(filePath: str, sampleBytes: int = 8192) -> bool:
    """
    Attempt to read the first N bytes and detect if file is text.
    Returns True if readable as UTF-8 or latin-1 text.
    """
    try:
        with open(filePath, "rb") as f:
            raw = f.read(sampleBytes)
        # Null byte strongly suggests binary
        if b"\x00" in raw:
            return False
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            raw.decode("latin-1")
            return True
        except Exception:
            return False
    except Exception:
        return False


def getFileExtension(filePath: str) -> str:
    _, ext = os.path.splitext(filePath)
    return ext.lower() if ext else "(none)"
