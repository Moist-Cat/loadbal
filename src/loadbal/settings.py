from pathlib import Path
import sys

DEBUG = True

BASE_DIR = Path(__file__).parent

HOST = "localhost"
PORT = 9999
RETRIES = 5

LOG_FILE = BASE_DIR / "logs/client.audit"
ERROR_FILE = BASE_DIR / "logs/client.error"
LOGGERS = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stderr,
            "formatter": "basic",
        },
        "audit_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 5000000,
            "backupCount": 1,
            "filename": LOG_FILE,
            "encoding": "utf-8",
            "formatter": "basic",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 5000000,
            "backupCount": 1,
            "filename": ERROR_FILE,
            "encoding": "utf-8",
            "formatter": "basic",
        },
    },
    "formatters": {
        "basic": {
            "style": "{",
            "format": "{asctime:s} [{levelname:s}] -- {name:s}: {message:s}",
        }
    },
    "loggers": {
        "user_info": {
            "handlers": ("console",),
            "level": "INFO" if DEBUG is False else "DEBUG",
        },
        "error": {"handlers": ("error_file",), "level": "ERROR"},
        "audit": {"handlers": ("audit_file",), "level": "DEBUG"},
    },
}
