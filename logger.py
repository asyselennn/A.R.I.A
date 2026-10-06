import logging
from config import LOG_FILE


def get_logger() -> logging.Logger:
    logger = logging.getLogger("ARIA")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger


logger = get_logger()
