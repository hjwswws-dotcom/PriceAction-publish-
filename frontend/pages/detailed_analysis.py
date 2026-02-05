"""
详细分析页 - 展示AI的完整价格行为分析
集成K线图与AI信号标记
"""

import streamlit as st
from database.db_manager import DatabaseManager
from frontend.components.chart_display import display_chart_with_controls


def show():
    """显示详细分析页面"""
    st.title("📊 详细价格行为分析")

    # 获取所有交易对状态
    db = DatabaseManager("./data.db")
    states = db.get_all_states()

    if not states:
        st.warning("暂无分析数据，请等待下一次分析周期")
        return

    # 交易对选择（去重并排序）
    symbols = list(set([s.get("symbol") for s in states]))
    symbols.sort()  # 保持一致的顺序
    selected_symbol = st.selectbox("选择交易对:", symbols)

    # 获取选定交易对的状态
    state = next((s for s in states if s.get("symbol") == selected_symbol), None)

    if not state:
        st.error("无法获取选定交易对的数据")
        return

    # 显示更新时间和市场周期
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**交易对:** {state.get('symbol', 'Unknown')}")
    with col2:
        cycle = state.get("marketCycle", "Unknown")
        cycle_colors = {
            "BULL_TREND": "🟢",
            "BEAR_TREND": "🔴",
            "TRADING_RANGE": "🟡",
            "TRANSITION": "🟠",
        }
        cycle_emoji = cycle_colors.get(cycle, "⚪")
        st.markdown(f"**市场周期:** {cycle_emoji} {cycle}")
    with col3:
        last_updated = state.get("last_updated", 0)
        if last_updated:
            from datetime import datetime

            dt = datetime.fromtimestamp(last_updated / 1000)
            st.markdown(f"**更新时间:** {dt.strftime('%H:%M:%S')}")

    st.markdown("---")

    # === K线图表区域（新增）===
    st.markdown("### 📈 K线图表与AI信号")

    # 提取关键价位和形态信息
    active = state.get("activeNarrative", {})
    levels = active.get("key_levels", {})
    key_levels = {
        "entry_trigger": levels.get("entry_trigger", 0),
        "invalidation_level": levels.get("invalidation_level", 0),
        "profit_target_1": levels.get("profit_target_1", 0),
    }
    pattern_info = {
        "pattern_name": active.get("pattern_name", ""),
        "comment": active.get("comment", ""),
    }

    # 显示交互式图表
    try:
        display_chart_with_controls(
            symbol=selected_symbol,
            key_levels=key_levels,
            pattern_info=pattern_info,
            default_timeframe="15m",
        )
    except Exception as e:
        st.error(f"初始化图表失败: {e}")

    st.markdown("---")
    # === 详细分析文本 ===
    analysis_text = state.get("analysis_text", "")
    if analysis_text:
        st.markdown("### 📖 AI详细分析")
        st.markdown(analysis_text)
    else:
        st.info("暂无详细分析文本（旧数据或未生成）")

    st.markdown("---")

    # 显示关键价位
    st.markdown("### 🎯 关键价位")
    col1, col2, col3 = st.columns(3)
    active = state.get("activeNarrative", {})
    levels = active.get("key_levels", {})

    with col1:
        entry = levels.get("entry_trigger", 0)
        if entry:
            st.metric("入场触发", f"${entry:,.2f}")
        else:
            st.metric("入场触发", "N/A")

    with col2:
        stop = levels.get("invalidation_level", 0)
        if stop:
            st.metric("止损位", f"${stop:,.2f}")
        else:
            st.metric("止损位", "N/A")

    with col3:
        target = levels.get("profit_target_1", 0)
        if target:
            st.metric("目标位", f"${target:,.2f}")
        else:
            st.metric("目标位", "N/A")

    # 显示概率和风险回报比
    st.markdown("---")
    st.markdown("### 🎯 概率与风险回报")

    def get_probability_emoji(probability):
        if not probability:
            return "❓"
        prob_lower = probability.lower()
        if "high" in prob_lower:
            return "🟢"
        elif "medium" in prob_lower:
            return "🟡"
        elif "low" in prob_lower:
            return "🔴"
        return "❓"

    col1, col2 = st.columns(2)
    with col1:
        probability = active.get("probability", "")
        prob_value = active.get("probability_value", 0.0)
        emoji = get_probability_emoji(probability)
        if probability:
            display_text = f"{emoji} {probability}"
            if prob_value > 0:
                display_text += f" ({prob_value:.1f}%)"
            st.metric("交易概率", display_text)
        else:
            st.metric("交易概率", "N/A")

    with col2:
        risk_reward = active.get("risk_reward", 0.0)
        if risk_reward > 0:
            st.metric("风险回报比", f"1:{risk_reward:.2f}")
        else:
            st.metric("风险回报比", "N/A")

    # 显示形态信息
    st.markdown("---")
    st.markdown("### 📈 形态信息")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**主导形态:**")
        st.write(f"- 名称: {active.get('pattern_name', 'Unknown')}")
        st.write(f"- 状态: {active.get('status', 'Unknown')}")
        comment = active.get("comment", "")
        if comment:
            st.write(f"- 说明: {comment}")

    with col2:
        alternative = state.get("alternativeNarrative", {})
        st.markdown("**备选剧本:**")
        st.write(f"- 名称: {alternative.get('pattern_name', 'None')}")
        trigger = alternative.get("trigger_condition", "")
        if trigger:
            st.write(f"- 触发: {trigger}")
