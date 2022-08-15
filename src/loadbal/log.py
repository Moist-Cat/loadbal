import logging
import logging.config
from typing import Callable

from loadbal import settings

logging.config.dictConfig(settings.LOGGERS)


def logged(cls) -> Callable:
    "Class decorator for logging purposes"

    cls.logger = logging.getLogger("user_info." + cls.__qualname__)
    cls.logger_error = logging.getLogger("audit." + cls.__qualname__)

    return cls

