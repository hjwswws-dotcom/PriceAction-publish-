"""Logger module for PriceAction"""

import logging
import colorlog
from pathlib import Path
from datetime import datetime


class ColorFormatter(colorlog.ColoredFormatter):
    """Custom colored formatter"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def setup_logger(name: str = "priceaction") -> logging.Logger:
    """Setup logger with console and file handlers"""

    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # File handler
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(f"logs/system_{timestamp}.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Format
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    console_formatter = ColorFormatter(
        fmt,
        date_fmt,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )

    file_formatter = logging.Formatter(fmt, date_fmt)

    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "priceaction") -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)


# Create global logger instance
logger = setup_logger()
