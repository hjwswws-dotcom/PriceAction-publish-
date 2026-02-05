"""
K线图展示组件
使用Plotly绘制交互式K线图，支持EMA均线、信号标记和形态区域高亮
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from frontend.components.indicators import (
    add_indicators_to_df,
    calculate_swing_points,
    identify_pattern_zones,
)


@st.cache_data(ttl=300)  # 5分钟缓存
def fetch_cached_klines(symbol: str, timeframe: str, limit: int):
    """获取K线数据（无fallback，数据获取失败则抛出异常）"""
    from src.config.settings import get_settings
    from src.data_provider.ccxt_fetcher import CCXTFetcher

    settings = get_settings()
    # 确保使用 settings.proxy (对应 .env 中的 PRICEACTION_EXCHANGE_PROXY)
    fetcher = CCXTFetcher(
        exchange_id=settings.exchange_id, proxy=settings.proxy, options={"defaultType": "swap"}
    )

    data = fetcher.fetch_ohlcv(symbol, timeframe, limit)

    if data is None or len(data) == 0:
        st.error(f"无法获取 {symbol} 数据，请检查代理是否配置为 {settings.proxy}")
        return None

    # 统一转换为 DataFrame，这是 Streamlit 绘图最稳的数据格式
    df = pd.DataFrame(data)
    return df


def create_kline_chart(
    klines: List[Dict],
    symbol: str,
    timeframe: str,
    key_levels: Optional[Dict] = None,
    pattern_info: Optional[Dict] = None,
    show_ema: bool = True,
    show_volume: bool = True,
    show_swing_points: bool = True,
    show_zones: bool = True,
) -> go.Figure:
    """创建K线图"""

    if klines is None or len(klines) == 0:
        raise ValueError("K线数据为空")

    # 转换为DataFrame
    df = pd.DataFrame(klines)
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("datetime", inplace=True)

    # 添加技术指标
    if show_ema:
        df = add_indicators_to_df(df)

    # 计算摆动点
    swing_points = calculate_swing_points(df) if show_swing_points else []

    # 识别形态区域
    pattern_zones = identify_pattern_zones(df) if show_zones else []

    # 创建图表
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(f"{symbol} {timeframe} K线图", "成交量"),
        row_heights=[0.7, 0.3],
    )

    # K线
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K线",
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
    if swing_points:
        swing_highs = [(p["time"], p["high"]) for p in swing_points if p["type"] == "high"]
        swing_lows = [(p["time"], p["low"]) for p in swing_points if p["type"] == "low"]

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

    # 形态区域
    if pattern_zones:
        for zone in pattern_zones:
            fig.add_vrect(
                x0=zone["start"],
                x1=zone["end"],
                fillcolor="orange",
                opacity=0.1,
                line_width=0,
                annotation_text=zone.get("name", ""),
                row=1,
                col=1,
            )

    # 隐藏周末空白
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

    # 更新布局
    fig.update_layout(
        title=dict(text=f"{symbol} {timeframe} 价格行为分析", x=0.5),
        template="plotly_dark",
        height=700,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    # 隐藏网格
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#333333")

    return fig


def display_chart_with_controls(
    symbol: str = "Unknown",
    timeframe: str = "15m",
    show_ema: bool = True,
    show_volume: bool = True,
    show_swing_points: bool = True,
    show_zones: bool = True,
    key_levels: list = None,
    pattern_info: dict = None,
    **kwargs,
):
    """带控制按钮的K线图展示
    兼容各种调用方式，**kwargs 吸收多余参数防止报错
    """
    # 从 kwargs 中获取可能的参数
    timeframe = kwargs.get("default_timeframe", timeframe)
    symbol = kwargs.get("symbol", symbol)

    # 如果传入 df，直接使用；否则从数据库获取
    df = kwargs.get("df")

    # 尝试获取数据，优先从数据库获取
    try:
        from database import DatabaseManager

        db = DatabaseManager("./data.db")
        db._ensure_connection()
        state = db.get_state(symbol, timeframe)
        db.close()

        # 尝试从数据库获取时间戳
        last_updated = state.get("last_updated") if state else None
        use_cache = False

        # 如果数据超过5分钟，重新获取
        if last_updated:
            import time

            if time.time() * 1000 - last_updated > 5 * 60 * 1000:
                use_cache = False

        # 获取K线数据
        klines = fetch_cached_klines(symbol, timeframe, limit=100)

        # klines 实际上是 DataFrame，需要用 .empty 检查
        if klines is None or (hasattr(klines, "empty") and klines.empty):
            st.error(f"无法获取 {symbol} 的K线数据，请检查网络连接")
            return

        # 获取分析状态用于显示关键价位
        key_levels = None
        pattern_info = None

        try:
            from database import DatabaseManager

            db = DatabaseManager("./data.db")
            db._ensure_connection()
            state = db.get_state(symbol, timeframe)
            db.close()

            if state:
                active_narrative_str = state.get("activeNarrative", "{}")
                import json

                if isinstance(active_narrative_str, str):
                    try:
                        active_narrative = json.loads(active_narrative_str)
                        key_levels = {"levels": []}

                        if "key_levels" in active_narrative:
                            kl = active_narrative["key_levels"]
                            if "entry_trigger" in kl:
                                key_levels["levels"].append(
                                    {"price": kl["entry_trigger"], "type": "entry"}
                                )
                            if "invalidation_level" in kl:
                                key_levels["levels"].append(
                                    {"price": kl["invalidation_level"], "type": "invalidation"}
                                )
                            if "profit_target_1" in kl:
                                key_levels["levels"].append(
                                    {"price": kl["profit_target_1"], "type": "target"}
                                )
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

        # 绘制图表
        fig = create_kline_chart(
            klines,
            symbol,
            timeframe,
            key_levels=key_levels,
            pattern_info=pattern_info,
            show_ema=show_ema,
            show_volume=show_volume,
            show_swing_points=show_swing_points,
            show_zones=show_zones,
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"图表渲染失败: {e}")
