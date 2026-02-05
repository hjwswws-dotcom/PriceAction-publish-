"""
技术指标计算模块
计算EMA、摆动高低点等技术指标
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """计算指数移动平均线"""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_swing_points(df: pd.DataFrame, window: int = 5) -> Dict:
    """
    识别摆动高低点 (Swing High/Low)

    Args:
        df: DataFrame with columns ['high', 'low', 'close']
        window: 左右各window根K线作为比较范围

    Returns:
        {
            'swing_highs': [(index, price), ...],
            'swing_lows': [(index, price), ...]
        }
    """
    swing_highs = []
    swing_lows = []

    for i in range(window, len(df) - window):
        # 检查摆动高点
        high = df.iloc[i]["high"]
        is_swing_high = all(
            high > df.iloc[j]["high"] for j in range(i - window, i + window + 1) if j != i
        )
        if is_swing_high:
            swing_highs.append((i, high))

        # 检查摆动低点
        low = df.iloc[i]["low"]
        is_swing_low = all(
            low < df.iloc[j]["low"] for j in range(i - window, i + window + 1) if j != i
        )
        if is_swing_low:
            swing_lows.append((i, low))

    return {"swing_highs": swing_highs, "swing_lows": swing_lows}


def add_indicators_to_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    为DataFrame添加所有技术指标

    Args:
        df: DataFrame with OHLCV data

    Returns:
        添加了技术指标的DataFrame
    """
    df = df.copy()

    # EMA
    df["ema20"] = calculate_ema(df["close"], 20)
    df["ema50"] = calculate_ema(df["close"], 50)

    return df


def identify_pattern_zones(
    df: pd.DataFrame,
    pattern_name: str = "Unknown",
    entry_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    target_price: Optional[float] = None,
) -> List[Dict]:
    """
    识别形态区域用于图表高亮

    根据形态类型和关键价位，确定需要高亮的区域

    Args:
        df: K线DataFrame
        pattern_name: 形态名称 (如 "High 2 Bull Flag", "Double Top")
        entry_price: 入场价位
        stop_price: 止损价位
        target_price: 目标价位

    Returns:
        区域列表,每个区域包含:
        {
            'x0': 起始时间,
            'x1': 结束时间,
            'y0': 下边界价格,
            'y1': 上边界价格,
            'type': 区域类型 (entry_zone/target_zone/invalidation_zone/pattern_zone),
            'color': 颜色,
            'name': 区域名称
        }
    """
    zones = []

    if len(df) < 10:
        return zones

    # 获取最近的价格范围作为默认区域
    recent_df = df.tail(30)  # 最近30根K线
    recent_high = recent_df["high"].max()
    recent_low = recent_df["low"].min()
    start_time = recent_df.iloc[0]["datetime"]
    end_time = recent_df.iloc[-1]["datetime"]

    # 根据形态类型确定区域
    pattern_lower = pattern_name.lower() if pattern_name else ""

    # 入场区域 (入场价附近的支撑/阻力区域)
    if entry_price and entry_price > 0:
        # 入场区域: 入场价 ± 0.3%
        zone_range = entry_price * 0.003
        zones.append(
            {
                "x0": start_time,
                "x1": end_time,
                "y0": entry_price - zone_range,
                "y1": entry_price + zone_range,
                "type": "entry_zone",
                "color": "rgba(33, 150, 243, 0.15)",  # 淡蓝色
                "name": f"入场区域 (${entry_price:,.2f})",
            }
        )

    # 止损区域
    if stop_price and stop_price > 0:
        zone_range = (
            abs(stop_price - (entry_price or stop_price)) * 0.2
            if entry_price
            else stop_price * 0.002
        )
        zones.append(
            {
                "x0": start_time,
                "x1": end_time,
                "y0": stop_price - zone_range,
                "y1": stop_price + zone_range,
                "type": "invalidation_zone",
                "color": "rgba(244, 67, 54, 0.15)",  # 淡红色
                "name": f"止损区域 (${stop_price:,.2f})",
            }
        )

    # 目标区域
    if target_price and target_price > 0:
        zone_range = (
            abs(target_price - (entry_price or target_price)) * 0.2
            if entry_price
            else target_price * 0.002
        )
        zones.append(
            {
                "x0": start_time,
                "x1": end_time,
                "y0": target_price - zone_range,
                "y1": target_price + zone_range,
                "type": "target_zone",
                "color": "rgba(76, 175, 80, 0.15)",  # 淡绿色
                "name": f"目标区域 (${target_price:,.2f})",
            }
        )

    # 形态特定区域
    if "flag" in pattern_lower or "channel" in pattern_lower:
        # 旗形/通道: 高亮最近的高低点形成的区域
        swing_points = calculate_swing_points(df.tail(20), window=2)
        if swing_points["swing_highs"] and swing_points["swing_lows"]:
            highs = [price for _, price in swing_points["swing_highs"]]
            lows = [price for _, price in swing_points["swing_lows"]]
            zones.append(
                {
                    "x0": start_time,
                    "x1": end_time,
                    "y0": min(lows[-3:]) if len(lows) >= 3 else min(lows),
                    "y1": max(highs[-3:]) if len(highs) >= 3 else max(highs),
                    "type": "pattern_zone",
                    "color": "rgba(255, 152, 0, 0.1)",  # 淡橙色
                    "name": "形态区域 (通道/旗形)",
                }
            )

    elif "double" in pattern_lower:
        # 双顶/双底: 高亮两个顶/底之间的区域
        recent_df = df.tail(30).reset_index(drop=True)
        swing_points = calculate_swing_points(recent_df, window=3)
        if len(swing_points["swing_highs"]) >= 2:
            # 双顶
            highs = swing_points["swing_highs"][-2:]  # 最近两个高点
            zones.append(
                {
                    "x0": recent_df.iloc[highs[0][0]]["datetime"],
                    "x1": recent_df.iloc[highs[1][0]]["datetime"],
                    "y0": min(highs[0][1], highs[1][1]) * 0.998,
                    "y1": max(highs[0][1], highs[1][1]) * 1.002,
                    "type": "pattern_zone",
                    "color": "rgba(156, 39, 176, 0.15)",  # 淡紫色
                    "name": "双顶形态区域",
                }
            )
        elif len(swing_points["swing_lows"]) >= 2:
            # 双底
            lows = swing_points["swing_lows"][-2:]  # 最近两个低点
            zones.append(
                {
                    "x0": recent_df.iloc[lows[0][0]]["datetime"],
                    "x1": recent_df.iloc[lows[1][0]]["datetime"],
                    "y0": min(lows[0][1], lows[1][1]) * 0.998,
                    "y1": max(lows[0][1], lows[1][1]) * 1.002,
                    "type": "pattern_zone",
                    "color": "rgba(156, 39, 176, 0.15)",  # 淡紫色
                    "name": "双底形态区域",
                }
            )

    elif "range" in pattern_lower or " consolidation" in pattern_lower:
        # 震荡区间: 高亮整个区间
        zones.append(
            {
                "x0": start_time,
                "x1": end_time,
                "y0": recent_low,
                "y1": recent_high,
                "type": "pattern_zone",
                "color": "rgba(158, 158, 158, 0.1)",  # 淡灰色
                "name": "震荡区间",
            }
        )

    elif "wedge" in pattern_lower:
        # 楔形: 高亮收敛区域
        swing_points = calculate_swing_points(df.tail(25), window=2)
        if swing_points["swing_highs"] and swing_points["swing_lows"]:
            highs = [price for _, price in swing_points["swing_highs"]]
            lows = [price for _, price in swing_points["swing_lows"]]
            zones.append(
                {
                    "x0": start_time,
                    "x1": end_time,
                    "y0": min(lows),
                    "y1": max(highs),
                    "type": "pattern_zone",
                    "color": "rgba(0, 150, 136, 0.1)",  # 淡青色
                    "name": "楔形收敛区域",
                }
            )

    return zones
