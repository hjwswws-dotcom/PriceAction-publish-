"""
交易信号面板页面 (Trading Signals Panel)
展示推荐信号和警告信号
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 页面配置
st.set_page_config(page_title="交易信号 | AI价格行为分析", page_icon="🚨", layout="wide")

from database import DatabaseManager


def format_timestamp(ts: int) -> str:
    """格式化时间戳"""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromtimestamp(ts / 1000)
        return dt.strftime("%m-%d %H:%M")
    except:
        return "N/A"


def get_signal_badge(level: str) -> str:
    """获取信号等级徽章"""
    badges = {"RECOMMENDED": "🟢 推荐", "WARNING": "🟡 警告", "INFO": "⚪ 普通"}
    return badges.get(level, level)


def get_outcome_badge(outcome: str) -> str:
    """获取结果徽章"""
    badges = {
        "WIN": "✅ 盈利",
        "LOSS": "❌ 亏损",
        "PENDING": "⏳ 持仓中",
        "EXPIRED": "⏰ 已过期",
    }
    return badges.get(outcome, outcome or "未知")


def display_signal_card(signal: Dict):
    """显示信号卡片"""
    signal_level = signal.get("signal_level", "INFO")
    pattern_name = signal.get("pattern_name", "Unknown")

    # 根据等级设置样式
    if signal_level == "RECOMMENDED":
        border_color = "#00cc00"
        bg_color = "#f0fff0"
    elif signal_level == "WARNING":
        border_color = "#ffaa00"
        bg_color = "#fffaf0"
    else:
        border_color = "#cccccc"
        bg_color = "#f9f9f9"

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
                {get_signal_badge(signal_level)} | {signal.get("symbol", "")}
            </h4>
            <p style="margin: 5px 0; font-size: 14px;">
                <strong>形态:</strong> {pattern_name} 
                (质量: {signal.get("pattern_quality", 0)}/5)
            </p>
            <p style="margin: 5px 0; font-size: 14px;">
                <strong>置信度:</strong> {signal.get("confidence", 0)}% | 
                <strong>盈亏比:</strong> 1:{signal.get("risk_reward_ratio", 0):.1f}
            </p>
            <p style="margin: 5px 0; font-size: 13px; color: #666;">
                {signal.get("description", "")}
            </p>
            <p style="margin: 5px 0; font-size: 12px; color: #999;">
                触发时间: {format_timestamp(signal.get("timestamp", 0))}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 展开查看详情
        with st.expander("查看详情"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**入场位**")
                entry = signal.get("entry_trigger", 0)
                st.write(f"{entry:.2f}" if entry else "N/A")

            with col2:
                st.markdown("**止损位**")
                stop = signal.get("stop_loss", 0)
                st.write(f"{stop:.2f}" if stop else "N/A")

            with col3:
                st.markdown("**目标位**")
                target = signal.get("profit_target_1", 0)
                st.write(f"{target:.2f}" if target else "N/A")

            # AI分析文本
            ai_analysis = signal.get("ai_analysis", "")
            if ai_analysis:
                st.markdown("**AI分析**")
                st.write(ai_analysis[:300] + "..." if len(ai_analysis) > 300 else ai_analysis)

            # 成交量信息
            vol_ratio = signal.get("volume_ratio")
            if vol_ratio:
                st.markdown("**成交量**")
                vol_sig = signal.get("volume_significance", "normal")
                st.write(f"{vol_ratio:.2f}x 平均 ({vol_sig})")


def main():
    """主函数"""
    st.title("🚨 实时交易信号面板")
    st.markdown("---")

    # 初始化数据库
    try:
        import os

        # 使用绝对路径
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data.db"
        )
        db = DatabaseManager(db_path)
        db._ensure_connection()  # 确保在当前线程建立连接
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return

    # 侧边栏筛选
    st.sidebar.header("筛选条件")

    # 信号等级筛选 - 默认显示所有信号类型
    signal_levels = st.sidebar.multiselect(
        "信号等级",
        options=["RECOMMENDED", "WARNING", "INFO"],
        default=["RECOMMENDED", "WARNING", "INFO"],  # 默认显示所有信号
        help="选择要显示的信号等级。INFO为普通状态更新，WARNING为警告，RECOMMENDED为推荐交易",
    )

    # 时间范围筛选
    time_range = st.sidebar.selectbox(
        "时间范围", options=["最近24小时", "最近3天", "最近7天", "全部"], index=0
    )

    # 转换时间范围为小时
    hours_map = {"最近24小时": 24, "最近3天": 72, "最近7天": 168, "全部": 0}
    hours = hours_map.get(time_range, 24)

    # 自动刷新
    auto_refresh = st.sidebar.checkbox("自动刷新 (30秒)", value=False)
    if auto_refresh:
        st.sidebar.info("页面将每30秒自动刷新")
        st.empty()

    # 获取信号数据
    all_signals = []  # 初始化
    filtered_signals = []  # 初始化

    try:
        # 使用新方法获取所有信号
        all_signals = db.get_all_signals(limit=200, hours=hours if hours > 0 else 0)

        # 按等级筛选
        filtered_signals = [s for s in all_signals if s.get("signal_level") in signal_levels]

        # 按时间排序
        filtered_signals.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        # 显示统计信息
        st.sidebar.metric("总信号数", len(all_signals))
        st.sidebar.metric("筛选后", len(filtered_signals))

    except Exception as e:
        st.error(f"获取信号数据失败: {e}")
        import traceback

        st.error(traceback.format_exc())
        all_signals = []
        filtered_signals = []

    # 主界面：显示活跃信号列表
    st.header("活跃信号")

    # 分离推荐信号和警告信号
    recommended_signals = [s for s in filtered_signals if s.get("signal_level") == "RECOMMENDED"]
    warning_signals = [s for s in filtered_signals if s.get("signal_level") == "WARNING"]

    # 显示推荐信号
    if recommended_signals:
        st.subheader(f"🟢 推荐交易信号 ({len(recommended_signals)})")
        for signal in recommended_signals[:5]:  # 只显示前5个
            display_signal_card(signal)
    else:
        st.info("暂无推荐信号")

    # 显示警告信号
    if warning_signals:
        st.subheader(f"🟡 警告信号 ({len(warning_signals)})")
        for signal in warning_signals[:5]:
            display_signal_card(signal)
    else:
        st.success("暂无警告信号")

    # 底部说明
    st.markdown("---")
    st.caption("""
    **信号等级说明:**
    - 🟢 **推荐信号**: 多周期共振 + 高置信度 + 理想盈亏比 (≥1:2) + 高胜率形态
    - 🟡 **警告信号**: 关键位突破 / 形态失效 / 结构破坏 / 流动性剧变
    - ⚪ **普通更新**: 状态变化但不构成交易机会
    """)


if __name__ == "__main__":
    main()
