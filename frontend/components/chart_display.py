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
    """带缓存的K线数据获取"""
    # 使用项目的CCXT fetcher
    from src.data_provider.ccxt_fetcher import CCXTFetcher
    from src.config.settings import get_settings
    import pandas as pd

    settings = get_settings()

    fetcher = CCXTFetcher(
        api_key=settings.exchange.binance_api_key or "",
        secret=settings.exchange.binance_secret or "",
        proxy=settings.exchange.proxy,
    )

    # 获取数据
    data = fetcher.fetch_ohlcv(symbol, timeframe, limit)

    # 转换为pandas DataFrame格式
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
        return []


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
    """
    创建K线图

    Args:
        klines: OHLCV数据列表
        symbol: 交易对名称
        timeframe: 时间框架
        key_levels: 关键价位 {'entry_trigger': float, 'invalidation_level': float, 'profit_target_1': float}
        pattern_info: 形态信息 {'pattern_name': str, 'comment': str}
        show_ema: 是否显示EMA均线
        show_volume: 是否显示成交量
        show_swing_points: 是否标记摆动高低点
        show_zones: 是否显示形态区域高亮

    Returns:
        Plotly Figure对象
    """
    # 转换为DataFrame
    df = pd.DataFrame(klines)
    # 转换为本地时间显示（从UTC）
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(
        "Asia/Shanghai"
    )

    # 添加技术指标
    if show_ema:
        df = add_indicators_to_df(df)

    # 创建子图布局 (K线图 + 成交量)
    if show_volume:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.8, 0.2],
            subplot_titles=(f"{symbol} {timeframe}", "Volume"),
        )
    else:
        fig = go.Figure()

    # 添加形态区域高亮（在K线之前，确保在底层）
    if show_zones and pattern_info:
        zones = identify_pattern_zones(
            df,
            pattern_name=pattern_info.get("pattern_name", ""),
            entry_price=key_levels.get("entry_trigger") if key_levels else None,
            stop_price=key_levels.get("invalidation_level") if key_levels else None,
            target_price=key_levels.get("profit_target_1") if key_levels else None,
        )

        for zone in zones:
            fig.add_vrect(
                x0=zone["x0"],
                x1=zone["x1"],
                y0=zone["y0"],
                y1=zone["y1"],
                fillcolor=zone["color"],
                line_width=1,
                line_dash="dot",
                line_color=zone["color"].replace("0.15", "0.5").replace("0.1", "0.4"),
                opacity=1,
                annotation_text=zone["name"],
                annotation_position="top left",
                annotation_font_size=10,
                row=1,
                col=1,
            )

    # 添加K线
    candlestick = go.Candlestick(
        x=df["datetime"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="K线",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    )

    if show_volume:
        fig.add_trace(candlestick, row=1, col=1)
    else:
        fig.add_trace(candlestick)

    # 添加EMA均线
    if show_ema and "ema20" in df.columns and "ema50" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["datetime"],
                y=df["ema20"],
                mode="lines",
                name="EMA20",
                line=dict(color="#2196f3", width=1.5),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["datetime"],
                y=df["ema50"],
                mode="lines",
                name="EMA50",
                line=dict(color="#ff9800", width=1.5),
            ),
            row=1,
            col=1,
        )

    # 添加摆动高低点标记
    if show_swing_points:
        swing_points = calculate_swing_points(df, window=3)

        # 摆动高点
        if swing_points["swing_highs"]:
            high_indices, high_prices = zip(*swing_points["swing_highs"])
            high_dates = df.iloc[list(high_indices)]["datetime"].tolist()
            fig.add_trace(
                go.Scatter(
                    x=high_dates,
                    y=high_prices,
                    mode="markers",
                    name="Swing High",
                    marker=dict(
                        symbol="triangle-down",
                        size=12,
                        color="#ff5252",
                        line=dict(width=2, color="white"),
                    ),
                ),
                row=1,
                col=1,
            )

        # 摆动低点
        if swing_points["swing_lows"]:
            low_indices, low_prices = zip(*swing_points["swing_lows"])
            low_dates = df.iloc[list(low_indices)]["datetime"].tolist()
            fig.add_trace(
                go.Scatter(
                    x=low_dates,
                    y=low_prices,
                    mode="markers",
                    name="Swing Low",
                    marker=dict(
                        symbol="triangle-up",
                        size=12,
                        color="#69f0ae",
                        line=dict(width=2, color="white"),
                    ),
                ),
                row=1,
                col=1,
            )

    # 添加关键价位水平线
    if key_levels:
        colors = {
            "entry_trigger": "#2196f3",  # 蓝色
            "invalidation_level": "#f44336",  # 红色
            "profit_target_1": "#4caf50",  # 绿色
        }
        dash_styles = {
            "entry_trigger": "solid",
            "invalidation_level": "dash",
            "profit_target_1": "dot",
        }
        names = {
            "entry_trigger": "🎯 入场",
            "invalidation_level": "🛑 止损",
            "profit_target_1": "💰 目标",
        }

        for key, value in key_levels.items():
            if value and value > 0:
                fig.add_hline(
                    y=value,
                    line_dash=dash_styles.get(key, "dash"),
                    line_color=colors.get(key, "#666"),
                    line_width=2,
                    annotation_text=f"{names.get(key, key)}: ${value:,.2f}",
                    annotation_position="right",
                    annotation_font_size=11,
                    annotation_font_color=colors.get(key, "#666"),
                    row=1,
                    col=1,
                )

    # 添加成交量
    if show_volume:
        colors = [
            "#26a69a" if close >= open else "#ef5350"
            for close, open in zip(df["close"], df["open"])
        ]
        fig.add_trace(
            go.Bar(
                x=df["datetime"],
                y=df["volume"],
                name="成交量",
                marker_color=colors,
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

    # 更新布局
    fig.update_layout(
        title=dict(
            text=f"{symbol} {timeframe} K线图",
            font=dict(size=16),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="时间",
        yaxis_title="价格",
        height=650 if show_volume else 550,
        template="plotly_white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
        ),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=60, t=80, b=60),
    )

    # 更新Y轴格式
    fig.update_yaxes(title_text="价格", gridcolor="rgba(0,0,0,0.05)", row=1, col=1)
    if show_volume:
        fig.update_yaxes(title_text="成交量", gridcolor="rgba(0,0,0,0.05)", row=2, col=1)

    fig.update_xaxes(gridcolor="rgba(0,0,0,0.05)")

    return fig


def display_chart_with_controls(
    symbol: str,
    key_levels: Optional[Dict] = None,
    pattern_info: Optional[Dict] = None,
    default_timeframe: str = "15m",
):
    """
    显示带控制面板的K线图

    Args:
        symbol: 交易对
        key_levels: AI分析的关键价位
        pattern_info: 形态信息
        default_timeframe: 默认时间框架
    """
    # 控制面板
    st.markdown("**📊 图表控制**")
    col1, col2, col3, col4 = st.columns([2, 2, 2, 4])

    with col1:
        timeframe = st.selectbox(
            "时间框架",
            options=["15m", "1h", "4h", "1d"],
            index=["15m", "1h", "4h", "1d"].index(default_timeframe)
            if default_timeframe in ["15m", "1h", "4h", "1d"]
            else 0,
            key=f"timeframe_{symbol}",
        )

    with col2:
        limit = st.slider(
            "K线数量",
            min_value=30,
            max_value=200,
            value=100,
            step=10,
            key=f"limit_{symbol}",
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh = st.button("🔄 刷新", key=f"refresh_{symbol}", width="stretch")

    # 图表选项
    with st.expander("⚙️ 显示选项", expanded=False):
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
    try:
        with st.spinner("📡 加载K线数据..."):
            if refresh:
                fetch_cached_klines.clear()
            klines = fetch_cached_klines(symbol, timeframe, limit)

        if not klines:
            st.error("❌ 无法获取K线数据")
            return

        # 创建图表
        fig = create_kline_chart(
            klines=klines,
            symbol=symbol,
            timeframe=timeframe,
            key_levels=key_levels,
            pattern_info=pattern_info,
            show_ema=show_ema,
            show_volume=show_volume,
            show_swing_points=show_swing,
            show_zones=show_zones,
        )

        # 显示图表
        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": True,
                "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"],
                "displaylogo": False,
            },
        )

        # 显示统计信息
        df = pd.DataFrame(klines)

        st.markdown("**📈 数据统计**")
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
            st.metric("成交量", f"{df['volume'].sum():,.0f}")

    except Exception as e:
        st.error(f"❌ 加载图表失败: {e}")
        st.exception(e)
