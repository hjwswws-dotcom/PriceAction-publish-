"""
Utility functions for PriceAction
"""

from datetime import datetime
from typing import Any, Dict, List


def format_timestamp(timestamp_ms: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp"""
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime(fmt)


def parse_timeframe(timeframe: str) -> int:
    """Convert timeframe to seconds"""
    units = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    return int(timeframe[:-1]) * units.get(timeframe[-1], 0)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to int"""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def format_price(price: float, symbol: str = "") -> str:
    """Format price display"""
    if symbol in ["BTC/USDT", "ETH/USDT"]:
        return f"{price:,.2f}"
    return f"{price:,.4f}"


def calculate_risk_reward(
    entry: float, stop: float, target: float, direction: str = "LONG"
) -> float:
    """Calculate risk/reward ratio"""
    if direction == "LONG":
        risk, reward = entry - stop, target - entry
    else:
        risk, reward = stop - entry, entry - target
    return round(reward / risk, 2) if risk > 0 else 0


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text"""
    return text[: max_length - len(suffix)] + suffix if len(text) > max_length else text


def batch_process(items: List[Any], batch_size: int = 10) -> List[List[Any]]:
    """Batch process list"""
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]
