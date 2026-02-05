"""
实战行动手册 - AI分析结果展示
包含：行动状态、方向、入场止损止盈、AI胜率、一键计算风险
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
from database import DatabaseManager
from src.config.settings import get_settings
from datetime import datetime
import json


def get_action_state_icon(state: str) -> tuple:
    """根据行动状态返回图标和颜色"""
    state_map = {
        "WAIT": ("⏳", "完全观望", "warning"),
        "CONDITIONAL": ("🔫", "挂单待命", "info"),
        "ENTER_NOW": ("🚀", "现价入场", "success"),
        "MANAGE_EXIT": ("🛑", "考虑离场", "error"),
    }
    return state_map.get(state, ("⚪", "未知", "secondary"))


def get_position_emoji(position: str) -> str:
    """仓位建议emoji"""
    emoji_map = {
        "NORMAL": "🟢 正常",
        "HALF": "🟡 减半",
        "AGGRESSIVE": "🔴 激进",
    }
    return emoji_map.get(position, "⚪ 未定义")


def show():
    """显示实战行动手册页面"""
    st.title("📘 实战行动手册 (Action Playbook)")

    # 获取所有状态
    try:
        db = DatabaseManager(get_settings().database_path)
        db._ensure_connection()  # 确保在当前线程建立连接
        states = db.get_all_states()
        db.close()
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return

    if not states:
        st.warning("暂无分析数据，请确保后端正在运行并完成首次分析")
        return

    st.caption("基于AI分析的客观行动建议，实时更新")

    for state in states:
        symbol = state.get("symbol", "Unknown")
        timeframe = state.get("timeframe", "15m")
        action = state.get("actionPlan")
        active_raw = state.get("activeNarrative", "{}")

        # 解析JSON字符串（如果需要）
        if isinstance(active_raw, str):
            try:
                active = json.loads(active_raw)
            except (json.JSONDecodeError, TypeError):
                active = {}
        else:
            active = active_raw

        # 解析actionPlan，兜底从activeNarrative提取
        raw_action = state.get("actionPlan")
        action = {}

        if raw_action:
            if isinstance(raw_action, str):
                try:
                    # 关键：将字符串转回字典
                    action = json.loads(raw_action)
                except Exception:
                    action = {}
            else:
                action = raw_action

        # 现在 action 确定是字典了，不再报错
        state_enum = action.get("state", "WAIT")
        direction = action.get("direction")
        order_type = action.get("orderType")
        entry_price = action.get("entryPrice")
        stop_loss = action.get("stopLoss")
        target_price = action.get("targetPrice")
        win_rate = action.get("winRateEst")
        suggested_position = action.get("suggestedPosition")
        reason = action.get("reason", "")

        # 兜底逻辑：从activeNarrative推导
        if not raw_action:
            state_enum = "WAIT"
            direction = None
            order_type = None
            entry_price = None
            stop_loss = None
            target_price = None
            win_rate = active.get("probability_value", 0.0)
            suggested_position = "NORMAL"
            reason = "无明确行动建议"

            # 如果有形态且状态是TRIGGERED，考虑设为ENTER_NOW
            pattern_status = active.get("status", "")
            if pattern_status == "TRIGGERED":
                state_enum = "ENTER_NOW"

        icon, state_text, color = get_action_state_icon(state_enum)

        # 主卡片
        with st.container():
            # 标题行
            col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
            with col_header1:
                st.subheader(f"{symbol} [{timeframe}]")
            with col_header2:
                st.caption(f"形态: {active.get('pattern_name', 'Unknown')}")

            # 状态大卡片
            st.markdown(f":{color}[**{icon} {state_text}**]")

            if reason:
                st.caption(f"原因: {reason}")

            st.divider()

            # 行动数据展示（非WAIT状态）
            if state_enum != "WAIT" and direction:
                # 第一行：方向、订单类型、入场
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    direction_emoji = "📈" if direction == "LONG" else "📉"
                    st.metric("方向", f"{direction_emoji} {direction}", order_type)

                with col2:
                    if entry_price:
                        st.metric("入场价", f"${entry_price:,.2f}")

                with col3:
                    if stop_loss:
                        st.metric("止损", f"${stop_loss:,.2f}")

                with col4:
                    if target_price:
                        st.metric("目标", f"${target_price:,.2f}")

                # 第二行：胜率、仓位建议
                col5, col6 = st.columns(2)

                with col5:
                    if win_rate:
                        win_percent = int(win_rate * 100) if win_rate <= 1 else int(win_rate)
                        st.metric("AI胜率", f"{win_percent}%", delta_color="normal")

                with col6:
                    st.metric("仓位建议", get_position_emoji(suggested_position))

                # 第三行：一键计算按钮
                st.divider()
                col_calc, col_spacer = st.columns([1, 3])

                with col_calc:
                    if st.button(
                        "⚡ 一键计算风险",
                        key=f"calc_{symbol}_{timeframe}",
                        type="primary",
                    ):
                        # 写入session_state
                        st.session_state["risk_calc_symbol"] = symbol
                        st.session_state["risk_calc_direction"] = direction
                        st.session_state["risk_calc_entry"] = entry_price
                        st.session_state["risk_calc_sl"] = stop_loss
                        st.session_state["risk_calc_tp"] = target_price
                        st.session_state["risk_calc_winrate"] = win_rate

                        # 跳转到风险计算器
                        st.session_state.nav_choice = "🎯 风险计算器"
                        st.rerun()

                # 盈亏比自动计算
                if entry_price and stop_loss and target_price:
                    risk = abs(entry_price - stop_loss)
                    reward = abs(target_price - entry_price)
                    if risk > 0:
                        rr = reward / risk
                        col_rr, _ = st.columns([1, 3])
                        with col_rr:
                            st.info(f"📊 预估盈亏比: **1:{rr:.2f}**")

            else:
                st.info("当前无明确入场建议，请关注形态发展")

            # 折叠显示详细分析
            with st.expander("查看主观详细分析 (Subjective Analysis)"):
                comment = active.get("comment", "")
                if comment:
                    st.markdown(f"**AI分析**: {comment}")
                else:
                    st.caption("无详细分析文本")

            # 时间戳
            last_updated = state.get("last_updated", 0)
            if last_updated:
                dt = datetime.fromtimestamp(last_updated / 1000)
                st.caption(f"更新: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # 每个交易对之间的分隔线
        st.markdown("---")


# 图例说明
st.markdown("### 📖 状态说明")
col_leg1, col_leg2, col_leg3, col_leg4 = st.columns(4)
with col_leg1:
    st.info("⏳ **完全观望**: 形态形成中，等待信号确认")
with col_leg2:
    st.info("🔫 **挂单待命**: 可设置限价/突破单等待触发")
with col_leg3:
    st.success("🚀 **现价入场**: 信号已触发，可考虑市价入场")
with col_leg4:
    st.error("🛑 **考虑离场**: 接近目标或触及止损位")

    # 刷新按钮
st.markdown("---")
if st.button("🔄 刷新数据", key="refresh_data"):
    st.rerun()

st.caption("💡 提示: 点击'一键计算风险'可跳转到风险计算器进行仓位规划")
