"""
K 线图展示组件 - 修复版
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from typing import Dict, Optional

from src.config.settings import get_settings
from frontend.components.indicators import (
    add_indicators_to_df,
    calculate_swing_points,
    identify_pattern_zones,
)


@st.cache_data(ttl=60)
def fetch_cached_klines(symbol: str, timeframe: str, limit: int):
    """获取 K 线数据"""
    from src.data_provider.ccxt_fetcher import CCXTFetcher

    settings = get_settings()
    fetcher = CCXTFetcher(
        exchange_id=settings.exchange_id, proxy=settings.proxy, options={"defaultType": "swap"}
    )

    data = fetcher.fetch_ohlcv(symbol, timeframe, limit)

    if data is None or len(data) == 0:
        return None

    df = pd.DataFrame(data)
    df.columns = [c.lower() for c in df.columns]

    # ✅ 唯一的时区转换点：使用 fromtimestamp 自动转为本地时间
    if "timestamp" in df.columns:
        df["datetime"] = df["timestamp"].apply(lambda x: datetime.fromtimestamp(x / 1000))

    return df


def create_kline_chart(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    key_levels: Optional[Dict] = None,
    show_ema: bool = True,
    show_volume: bool = True,
    show_swing_points: bool = True,
    show_zones: bool = True,
) -> go.Figure:
    """创建 K 线图"""

    if df is None or df.empty:
        raise ValueError("K 线数据为空")

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # 确保有 datetime 列
    if "datetime" not in df.columns:
        if "timestamp" in df.columns:
            df["datetime"] = df["timestamp"].apply(lambda x: datetime.fromtimestamp(x / 1000))
        else:
            raise ValueError("数据中缺少 datetime 或 timestamp 列")

    df = df.sort_values("datetime")
    df = df.set_index("datetime")

    # 添加技术指标
    if show_ema:
        df = add_indicators_to_df(df)

    # 计算摆动点
    swing_points = calculate_swing_points(df) if show_swing_points else []

    # 创建图表
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(f"{symbol} {timeframe} K 线图", "成交量"),
        row_heights=[0.7, 0.3],
    )

    # K 线
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K 线",
            increasing_line_color="#26A17E",
            decreasing_line_color="#E6444F",
        ),
        row=1,
        col=1,
    )

    # 成交量
    if show_volume and "volume" in df.columns:
        colors = [
            "#26A17E" if row["close"] >= row["open"] else "#E6444F" for _, row in df.iterrows()
        ]
        fig.add_trace(
            go.Bar(x=df.index, y=df["volume"], name="成交量", marker_color=colors),
            row=2,
            col=1,
        )

    # 摆动点
    if swing_points and isinstance(swing_points, dict):
        raw_highs = swing_points.get("swing_highs", [])
        raw_lows = swing_points.get("swing_lows", [])

        swing_highs = [(df.index[idx], price) for idx, price in raw_highs if idx < len(df)]
        swing_lows = [(df.index[idx], price) for idx, price in raw_lows if idx < len(df)]

        if swing_highs:
            fig.add_trace(
                go.Scatter(
                    x=[s[0] for s in swing_highs],
                    y=[s[1] for s in swing_highs],
                    mode="markers",
                    name="Swing High",
                    marker=dict(symbol="triangle-down", size=10, color="#E6444F"),
                ),
                row=1,
                col=1,
            )

        if swing_lows:
            fig.add_trace(
                go.Scatter(
                    x=[s[0] for s in swing_lows],
                    y=[s[1] for s in swing_lows],
                    mode="markers",
                    name="Swing Low",
                    marker=dict(symbol="triangle-up", size=10, color="#26A17E"),
                ),
                row=1,
                col=1,
            )

    # 关键价位
    if key_levels:
        for level in key_levels.get("levels", []):
            price = level.get("price")
            level_type = level.get("type", "support")
            color = "#26A17E" if level_type == "support" else "#E6444F"
            fig.add_hline(
                y=price,
                line=dict(color=color, width=1, dash="dash"),
                annotation_text=f"{price:,.2f}",
                row=1,
                col=1,
            )

    # 更新布局
    fig.update_layout(
        title=dict(text=f"{symbol} {timeframe} 价格行为分析", x=0.5),
        template="plotly_dark",
        height=700,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#333333")

    return fig


def display_chart_with_controls(
    symbol: str = "BTC/USDT:USDT",
    timeframe: str = "15m",
    show_ema: bool = True,
    show_volume: bool = True,
    show_swing_points: bool = True,
    show_zones: bool = True,
    key_levels: dict = None,
    pattern_info: dict = None,
    **kwargs,
):
    """带控制按钮的 K 线图展示"""

    # 兼容旧参数
    timeframe = kwargs.get("default_timeframe", timeframe)
    symbol = kwargs.get("symbol", symbol)

    try:
        # 获取数据
        df = fetch_cached_klines(symbol, timeframe, limit=100)

        if df is None or df.empty:
            st.warning("暂无 K 线数据")
            return

        # 获取关键价位
        try:
            from database import DatabaseManager
            import json

            db = DatabaseManager(get_settings().database_path)
            db._ensure_connection()
            state = db.get_state(symbol, timeframe)
            db.close()

            if state:
                active_str = state.get("activeNarrative", "{}")
                if isinstance(active_str, str):
                    try:
                        active = json.loads(active_str)
                        if "key_levels" in active:
                            kl = active["key_levels"]
                            key_levels = {"levels": []}
                            if kl.get("entry_trigger"):
                                key_levels["levels"].append(
                                    {"price": kl["entry_trigger"], "type": "entry"}
                                )
                            if kl.get("invalidation_level"):
                                key_levels["levels"].append(
                                    {"price": kl["invalidation_level"], "type": "stop"}
                                )
                            if kl.get("profit_target_1"):
                                key_levels["levels"].append(
                                    {"price": kl["profit_target_1"], "type": "target"}
                                )
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

        # 绘制图表
        fig = create_kline_chart(
            df,
            symbol,
            timeframe,
            key_levels=key_levels,
            show_ema=show_ema,
            show_volume=show_volume,
            show_swing_points=show_swing_points,
            show_zones=show_zones,
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"图表渲染失败: {e}")
