"""
新闻信号面板页面 (News Signals Panel)
展示实时新闻信号和风险警报
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 页面配置
st.set_page_config(
    page_title="📰 新闻信号 | AI价格行为分析", page_icon="📰", layout="wide"
)

# 添加项目根目录到路径
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.db_manager import DatabaseManager


def format_timestamp(ts: int) -> str:
    """格式化时间戳"""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromtimestamp(ts / 1000)
        return dt.strftime("%m-%d %H:%M")
    except:
        return "N/A"


def get_severity_badge(severity: str) -> str:
    """获取严重程度徽章"""
    badges = {
        "CRITICAL": "🔴 严重",
        "WARNING": "🟡 警告",
        "INFO": "🟢 信息",
    }
    return badges.get(severity, severity)


def get_event_icon(event_type: str) -> str:
    """获取事件类型图标"""
    icons = {
        "HACK_EXPLOIT": "💰",
        "DELISTING": "⚠️",
        "LISTING": "✅",
        "REGULATION": "📜",
        "RUMOR": "👂",
        "PARTNERSHIP": "🤝",
        "TOKENOMICS": "📊",
        "MACRO": "🌐",
        "TECHNICAL": "⚙️",
    }
    return icons.get(event_type, "📰")


def get_direction_icon(direction: str) -> str:
    """获取方向图标"""
    icons = {
        "bullish": "🐂 利好",
        "bearish": "🐻 利空",
        "unclear": "❓ 不明",
    }
    return icons.get(direction, "")


def display_news_signal_card(signal: Dict):
    """显示新闻信号卡片"""
    severity = signal.get("severity", "INFO")
    event_type = signal.get("event_type", "UNKNOWN")
    tail_risk = signal.get("tail_risk", 1)
    impact = signal.get("impact_volatility", 1)

    # 根据严重程度设置样式
    if severity == "CRITICAL":
        border_color = "#ff0000"
        bg_color = "#fff0f0"
    elif severity == "WARNING":
        border_color = "#ffaa00"
        bg_color = "#fffaf0"
    else:
        border_color = "#00aa00"
        bg_color = "#f0fff0"

    assets = signal.get("assets", [])
    assets_str = ", ".join(assets) if assets else "市场整体"

    # 构建卡片内容
    with st.container():
        st.markdown(
            f"""
        <div style="
            border-left: 5px solid {border_color};
            background-color: {bg_color};
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        ">
            <h4 style="margin: 0 0 10px 0;">
                {get_severity_badge(severity)} | {get_event_icon(event_type)} {event_type}
            </h4>
            <p style="margin: 5px 0; font-size: 14px;">
                <strong>受影响资产:</strong> {assets_str}
            </p>
            <p style="margin: 5px 0; font-size: 14px;">
                <strong>风险评估:</strong> 尾部风险={tail_risk}/5 | 波动影响={impact}/5
            </p>
            <p style="margin: 5px 0; font-size: 13px; color: #666;">
                <strong>核心观点:</strong> {signal.get("one_line_thesis", "N/A")[:200]}
            </p>
            <p style="margin: 5px 0; font-size: 12px; color: #999;">
                置信度: {signal.get("confidence", 0) * 100:.0f}% | 关注度: {signal.get("attention_score", 0) * 100:.0f}%
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 展开查看详情
        with st.expander("查看详情"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**事件类型**")
                st.write(f"{get_event_icon(event_type)} {event_type}")

            with col2:
                st.markdown("**方向判断**")
                direction = signal.get("direction_hint", "")
                st.write(get_direction_icon(direction))

            with col3:
                st.markdown("**时间范围**")
                time_horizon = signal.get("time_horizon", "unknown")
                st.write(time_horizon)

            # 完整分析
            full_analysis = signal.get("full_analysis", "")
            if full_analysis:
                st.markdown("**完整分析**")
                st.write(full_analysis)

            # 证据链接
            evidence_urls = signal.get("evidence_urls", [])
            if evidence_urls:
                st.markdown("**证据来源**")
                for url in evidence_urls[:3]:
                    st.write(f"- [{url}]({url})")


def main():
    """主函数"""
    st.title("📰 新闻信号面板")
    st.markdown("实时监控加密货币相关新闻，在高影响事件发生时提前预警")
    st.markdown("---")

    # 初始化数据库
    try:
        import os

        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data.db"
        )
        db = DatabaseManager(db_path)
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return

    # 侧边栏筛选
    st.sidebar.header("筛选条件")

    # 严重程度筛选
    severities = st.sidebar.multiselect(
        "严重程度",
        options=["CRITICAL", "WARNING", "INFO"],
        default=["CRITICAL", "WARNING", "INFO"],
    )

    # 时间范围筛选
    time_range = st.sidebar.selectbox(
        "时间范围", options=["最近6小时", "最近24小时", "最近7天", "全部"], index=0
    )

    # 转换时间范围为小时
    hours_map = {"最近6小时": 6, "最近24小时": 24, "最近7天": 168, "全部": 0}
    hours = hours_map.get(time_range, 24)

    # 资产筛选
    assets = st.sidebar.multiselect(
        "资产筛选",
        options=["BTC", "ETH", "XAG", "XAU", "SOL", "XRP", "ADA", "DOGE"],
        default=[],
    )

    # 自动刷新
    auto_refresh = st.sidebar.checkbox("自动刷新 (60秒)", value=False)
    if auto_refresh:
        st.sidebar.info("页面将每60秒自动刷新")
        st.empty()

    # 获取新闻信号数据
    try:
        if assets:
            news_signals = db.get_news_signals_by_assets(assets=assets, limit=100)
        else:
            news_signals = db.get_latest_news_signals(
                window_hours=hours if hours > 0 else 24,
                topk=100,
                min_rank_score=0.0,
            )

        # 按严重程度筛选
        filtered_signals = [s for s in news_signals if s.get("severity") in severities]

        # 按严重程度和时间排序
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        filtered_signals.sort(
            key=lambda x: (
                severity_order.get(x.get("severity", "INFO"), 3),
                x.get("created_time_utc", 0),
            ),
            reverse=True,
        )

        # 显示统计信息
        critical_count = len(
            [s for s in news_signals if s.get("severity") == "CRITICAL"]
        )
        warning_count = len([s for s in news_signals if s.get("severity") == "WARNING"])

        col1, col2, col3 = st.sidebar.columns(3)
        col1.metric("严重", critical_count)
        col2.metric("警告", warning_count)
        col3.metric("总计", len(news_signals))

    except Exception as e:
        st.error(f"获取新闻信号数据失败: {e}")
        import traceback

        st.error(traceback.format_exc())
        filtered_signals = []

    # 主界面：显示风险摘要
    st.header("当前风险状态")

    if filtered_signals:
        # 计算风险等级
        max_tail = max(s.get("tail_risk", 0) for s in filtered_signals)
        max_impact = max(s.get("impact_volatility", 0) for s in filtered_signals)

        if max_tail >= 3 or max_impact >= 4:
            risk_level = "🔴 高风险"
            risk_color = "#ff0000"
        elif max_tail >= 2 or max_impact >= 3:
            risk_level = "🟡 中等风险"
            risk_color = "#ffaa00"
        else:
            risk_level = "🟢 正常"
            risk_color = "#00aa00"

        st.markdown(
            f"""
        <div style="
            background-color: {risk_color}20;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        ">
            <h2 style="margin: 0; color: {risk_color};">{risk_level}</h2>
            <p style="margin: 5px 0;">最高尾部风险: {max_tail}/5 | 最高波动影响: {max_impact}/5</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.info("暂无新闻信号")

    # 主界面：显示新闻信号列表
    st.header("新闻信号列表")

    # 分离严重和警告信号
    critical_signals = [s for s in filtered_signals if s.get("severity") == "CRITICAL"]
    warning_signals = [s for s in filtered_signals if s.get("severity") == "WARNING"]
    info_signals = [s for s in filtered_signals if s.get("severity") == "INFO"]

    # 显示严重信号
    if critical_signals:
        st.subheader(f"🔴 严重信号 ({len(critical_signals)})")
        for signal in critical_signals[:10]:
            display_news_signal_card(signal)
    else:
        st.success("暂无严重信号")

    # 显示警告信号
    if warning_signals:
        st.subheader(f"🟡 警告信号 ({len(warning_signals)})")
        for signal in warning_signals[:10]:
            display_news_signal_card(signal)

    # 显示信息信号
    if info_signals:
        with st.expander(f"🟢 普通信息 ({len(info_signals)})"):
            for signal in info_signals[:10]:
                display_news_signal_card(signal)

    # 底部说明
    st.markdown("---")
    st.markdown("""
    **风险评估说明:**
    - 🔴 **严重信号**: 高尾部风险(≥3)或极高波动影响(≥4)，建议立即降低杠杆/仓位
    - 🟡 **警告信号**: 中等风险(≥2)，建议关注并可能调整止损
    - 🟢 **普通信息**: 低风险事件，正常交易即可
    """)

    st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
