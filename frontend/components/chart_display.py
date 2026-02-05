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
    proxy = settings.exchange_proxy

    fetcher = CCXTFetcher(
        api_key=proxy or "",
        secret="",
        proxy=proxy,
    )

    data = fetcher.fetch_ohlcv(symbol, timeframe, limit)

    # 转换为字典列表格式
    if hasattr(data, "ohlcv") and isinstance(data.ohlcv, list):
        klines = [
            {
                "timestamp": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5],
            }
            for candle in data.ohlcv
        ]
        return klines
    elif isinstance(data, list):
        return data
    else:
        raise ConnectionError(f"无法获取 {symbol} K线数据，请检查网络和代理设置")


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

    if not klines:
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
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{symbol} {timeframe} - K线图", "成交量"),
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
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    # 关键价位
    if key_levels and any(key_levels.values()):
        colors = {
            "entry_trigger": "#2196F3",
            "invalidation_level": "#f44336",
            "profit_target_1": "#4CAF50",
        }
        for level_name, price in key_levels.items():
            if price and price > 0:
                color = colors.get(level_name, "#9E9E9E")
                level_label = {
                    "entry_trigger": "入场",
                    "invalidation_level": "止损",
                    "profit_target_1": "止盈",
                }.get(level_name, level_name)

                fig.add_hline(
                    y=price,
                    line=dict(color=color, width=2, dash="dash"),
                    row=1,
                    col=1,
                    annotation_text=f"{level_label}: {price:,.2f}",
                    annotation_position="top right",
                )

    # 摆动高点和低点
    if swing_points:
        highs = [p for p in swing_points if p["type"] == "high"]
        lows = [p for p in swing_points if p["type"] == "low"]

        if highs:
            fig.add_trace(
                go.Scatter(
                    x=[p["time"] for p in highs],
                    y=[p["price"] for p in highs],
                    mode="markers",
                    marker=dict(symbol="triangle-down", size=8, color="#ef5350"),
                    name="摆动高点",
                ),
                row=1,
                col=1,
            )

        if lows:
            fig.add_trace(
                go.Scatter(
                    x=[p["time"] for p in lows],
                    y=[p["price"] for p in lows],
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=8, color="#26a69a"),
                    name="摆动低点",
                ),
                row=1,
                col=1,
            )

    # 形态区域
    if pattern_zones:
        for zone in pattern_zones[:5]:
            fig.add_vrect(
                x0=zone["start"],
                x1=zone["end"],
                fillcolor=zone.get("color", "#9E9E9E"),
                opacity=0.2,
                line_width=0,
                row=1,
                col=1,
            )

    # EMA均线
    if show_ema and "EMA_20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["EMA_20"],
                mode="lines",
                line=dict(color="#FF9800", width=1.5),
                name="EMA20",
            ),
            row=1,
            col=1,
        )

    # 成交量
    if show_volume:
        colors = [
            "#26a69a" if close >= open else "#ef5350"
            for open, close in zip(df["open"], df["close"])
        ]
        fig.add_trace(
            go.Bar(x=df.index, y=df["volume"], marker_color=colors, name="成交量"),
            row=2,
            col=1,
        )

    # 布局
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=700,
        template="plotly_dark",
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_xaxes(row=1, col=1, rangeslider=dict(visible=False))
    fig.update_xaxes(row=2, col=1, title_text="时间")

    return fig


def display_chart_with_controls(
    symbol: str,
    key_levels: Optional[Dict] = None,
    pattern_info: Optional[Dict] = None,
    default_timeframe: str = "15m",
):
    """显示交互式K线图（带控制面板）"""

    # 控制面板
    with st.expander("图表设置", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            show_ema = st.checkbox("EMA均线", value=True, key=f"ema_{symbol}")
        with col2:
            show_volume = st.checkbox("成交量", value=True, key=f"volume_{symbol}")
        with col3:
            show_swing = st.checkbox("摆动点", value=True, key=f"swing_{symbol}")
        with col4:
            show_zones = st.checkbox("形态区域", value=True, key=f"zones_{symbol}")

    # 获取数据
    with st.spinner("加载K线数据..."):
        try:
            klines = fetch_cached_klines(symbol, default_timeframe, 50)
        except Exception as e:
            st.error(f"获取数据失败: {e}")
            st.info("请检查: 1) VPN代理是否开启 2) 代理端口是否正确 (10806)")
            return

    if not klines:
        st.error("K线数据为空")
        return

    # 创建图表
    fig = create_kline_chart(
        klines=klines,
        symbol=symbol,
        timeframe=default_timeframe,
        key_levels=key_levels,
        pattern_info=pattern_info,
        show_ema=show_ema,
        show_volume=show_volume,
        show_swing_points=show_swing,
        show_zones=show_zones,
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": True,
            "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"],
            "displaylogo": False,
        },
    )

    # 统计信息
    df = pd.DataFrame(klines)
    st.markdown("**数据统计**")
    cols = st.columns(5)
    with cols[0]:
        st.metric("当前", f"${df['close'].iloc[-1]:,.2f}")
    with cols[1]:
        st.metric("最高", f"${df['high'].max():,.2f}")
    with cols[2]:
        st.metric("最低", f"${df['low'].min():,.2f}")
    with cols[3]:
        change = df["close"].iloc[-1] - df["close"].iloc[0]
        change_pct = (change / df["close"].iloc[0]) * 100
        st.metric("涨跌", f"{change:+.2f}", f"{change_pct:+.2f}%")
    with cols[4]:
        st.metric("成交量", f"{df['volume'].iloc[-1]:,.0f}")
