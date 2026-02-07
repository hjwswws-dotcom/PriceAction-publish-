"""
时区转换工具函数
提供 UTC 毫秒时间戳到北京时间字符串的转换
"""

from datetime import datetime, timezone, timedelta

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def utc_ms_to_beijing_str(utc_ms: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """将 UTC 毫秒时间戳转换为北京时间字符串

    Args:
        utc_ms: UTC 毫秒时间戳
        fmt: 输出格式，默认 "%Y-%m-%d %H:%M:%S"

    Returns:
        北京时间字符串，如 "2024-01-15 14:30:00"，无效输入返回 "N/A"
    """
    if not utc_ms:
        return "N/A"
    try:
        utc_dt = datetime.fromtimestamp(utc_ms / 1000, tz=timezone.utc)
        beijing_dt = utc_dt.astimezone(BEIJING_TZ)
        return beijing_dt.strftime(fmt)
    except (OSError, ValueError, TypeError):
        return "N/A"


def utc_ms_to_datetime(utc_ms: int) -> datetime | None:
    """将 UTC 毫秒时间戳转换为 datetime 对象（北京时间）

    Args:
        utc_ms: UTC 毫秒时间戳

    Returns:
        北京时间 datetime 对象，失败返回 None
    """
    if not utc_ms:
        return None
    try:
        utc_dt = datetime.fromtimestamp(utc_ms / 1000, tz=timezone.utc)
        return utc_dt.astimezone(BEIJING_TZ)
    except (OSError, ValueError, TypeError):
        return None
