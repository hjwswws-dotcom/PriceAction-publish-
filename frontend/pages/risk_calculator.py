"""
风险计算器页面
用户手动输入交易计划，获取AI风险分析和仓位建议
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional

# 导入项目模块
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db_manager import DatabaseManager
from core.research_assistant import ResearchAssistant
from core.risk_analyzer import RiskAnalyzer

# 交易对列表
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "XAG/USDT:USDT", "XAU/USDT:USDT"]
TIMEFRAMES = ["15m", "1h", "1d"]


def load_config(config_path: str = "config/config.json") -> dict:
    """
    加载配置文件
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as e:
        return {}


def show():
    """显示风险计算器页面（供app.py调用）"""

    # 页面配置
    st.set_page_config(page_title="风险计算器", page_icon="🎯", layout="wide")

    # 初始化
    @st.cache_resource
    def get_db_manager():
        return DatabaseManager("./data.db")

    @st.cache_resource
    def get_research_assistant():
        config = load_config()
        if config:
            return ResearchAssistant(config)
        return None

    @st.cache_resource
    def get_risk_analyzer():
        return RiskAnalyzer()

    db = get_db_manager()
    ra = get_research_assistant()
    risk_analyzer = get_risk_analyzer()

    st.title("🎯 AI风险计算器")
    st.markdown("输入您的交易计划，获取专业的AI风险评估和仓位建议")

    # ========== 预填数据处理 ==========
    # 检查是否从行动手册跳转而来
    has_preset = False
    preset_symbol = st.session_state.get("risk_calc_symbol")
    if preset_symbol:
        has_preset = True
        st.info("📋 已从实战行动手册填充数据，请确认后点击分析")

        # 从session_state读取预填数据
        default_symbol = preset_symbol
        default_direction = st.session_state.get("risk_calc_direction", "LONG")
        default_entry = st.session_state.get("risk_calc_entry", 0.0)
        default_sl = st.session_state.get("risk_calc_sl", 0.0)
        default_tp = st.session_state.get("risk_calc_tp", 0.0)
        default_winrate = st.session_state.get("risk_calc_winrate", 0.5)

        # 从symbol中提取基础币种用于查找index
        symbol_base = default_symbol.replace("/USDT:USDT", "").replace("/USDT", "")
    else:
        # 默认值
        default_symbol = "BTC/USDT:USDT"
        default_direction = "LONG"
        default_entry = 0.0
        default_sl = 0.0
        default_tp = 0.0
        default_winrate = 0.5

    # 计算selectbox的index
    def get_symbol_index(sym):
        try:
            return SYMBOLS.index(sym)
        except (ValueError, AttributeError):
            return 0

    def get_direction_index(dirc):
        return 0 if dirc == "LONG" else 1

    # ========== 创建两列布局 ==========
    col_input, col_result = st.columns([1, 1.5])

    with col_input:
        st.subheader("📋 交易计划")

        with st.form("trade_plan_form"):
            # 基本信息
            symbol = st.selectbox(
                "交易对", SYMBOLS, index=get_symbol_index(default_symbol)
            )
            direction = st.radio(
                "方向",
                ["LONG", "SHORT"],
                index=get_direction_index(default_direction),
                horizontal=True,
            )
            timeframe = st.selectbox("参考时间框架", TIMEFRAMES, index=0)

            # Phase 5.1: 关联分析师AI分析
            st.divider()
            use_analyst_context = st.checkbox(
                "🔗 关联分析师AI分析",
                value=True,
                help="将分析师AI的最新分析结果传递给风险AI，获得更精准的风险评估",
            )

            st.divider()

            # 价格设置（使用预填值）
            col1, col2 = st.columns(2)
            with col1:
                entry_price = st.number_input(
                    "入场价",
                    min_value=0.0,
                    value=float(default_entry)
                    if default_entry and default_entry > 0
                    else 0.0,
                    step=0.01,
                    format="%.2f",
                )
            with col2:
                stop_loss = st.number_input(
                    "止损价",
                    min_value=0.0,
                    value=float(default_sl) if default_sl and default_sl > 0 else 0.0,
                    step=0.01,
                    format="%.2f",
                )

            # 止盈设置
            col3, col4 = st.columns(2)
            with col3:
                take_profit_1 = st.number_input(
                    "第一目标位 (TP1)",
                    min_value=0.0,
                    value=float(default_tp) if default_tp and default_tp > 0 else 0.0,
                    step=0.01,
                    format="%.2f",
                )
            with col4:
                take_profit_2 = st.number_input(
                    "第二目标位 (TP2, 可选)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                )

            st.divider()

            # 风险评估参数（胜率使用预填值）
            col5, col6 = st.columns(2)
            with col5:
                # 计算滑块value，确保在10-90范围内
                win_value = (
                    int(default_winrate * 100) if 0 < default_winrate <= 1 else 50
                )
                win_probability = (
                    st.slider(
                        "估计胜率 (%)",
                        min_value=10,
                        max_value=90,
                        value=win_value,
                        step=5,
                    )
                    / 100.0
                )
            with col6:
                position_size_actual = st.slider(
                    "计划仓位 (%)", min_value=1, max_value=50, value=10, step=1
                )

            user_notes = st.text_area(
                "备注 (可选)", placeholder="记录您的交易理由或其他想法..."
            )

            submitted = st.form_submit_button(
                "🚀 AI风险分析", use_container_width=True, type="primary"
            )

    # 处理完预填数据后清除session_state
    if has_preset:
        for key in [
            "risk_calc_symbol",
            "risk_calc_direction",
            "risk_calc_entry",
            "risk_calc_sl",
            "risk_calc_tp",
            "risk_calc_winrate",
        ]:
            st.session_state.pop(key, None)

    # 结果显示区域
    with col_result:
        st.subheader("📊 风险分析结果")

        if submitted:
            # 验证输入
            if entry_price <= 0 or stop_loss <= 0 or take_profit_1 <= 0:
                st.error("❌ 请填写完整的入场价、止损价和第一目标位")
            elif (direction == "LONG" and stop_loss >= entry_price) or (
                direction == "SHORT" and stop_loss <= entry_price
            ):
                st.error(f"❌ {direction}方向的止损价设置不合理")
            elif (direction == "LONG" and take_profit_1 <= entry_price) or (
                direction == "SHORT" and take_profit_1 >= entry_price
            ):
                st.error(f"❌ {direction}方向的目标位设置不合理")
            else:
                with st.spinner("🤖 AI正在分析风险..."):
                    try:
                        # 1. 保存用户输入的交易计划
                        trade_plan = {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "direction": direction,
                            "entry_price": entry_price,
                            "stop_loss": stop_loss,
                            "take_profit_1": take_profit_1,
                            "take_profit_2": take_profit_2
                            if take_profit_2 > 0
                            else None,
                            "win_probability": win_probability,
                            "position_size_actual": position_size_actual,
                            "user_notes": user_notes,
                        }

                        analysis_id = db.create_risk_analysis(trade_plan)

                        # 2. 获取市场数据并计算基础风险指标
                        klines_15m = ra.fetcher.fetch_ohlcv(symbol, "15m", limit=50)
                        klines_1h = ra.fetcher.fetch_ohlcv(symbol, "1h", limit=50)
                        klines_1d = ra.fetcher.fetch_ohlcv(symbol, "1d", limit=50)

                        # Phase 5.2: 获取②类市场数据
                        market_context = ra.fetcher.fetch_market_context(symbol)

                        # 3. 计算风险指标
                        risk_metrics = risk_analyzer.calculate_risk_metrics(
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit_1=take_profit_1,
                            take_profit_2=take_profit_2 if take_profit_2 > 0 else None,
                            win_probability=win_probability,
                            klines_15m=klines_15m,
                            klines_1h=klines_1h,
                            klines_1d=klines_1d,
                            direction=direction,
                        )

                        # Phase 5.1: 如启用，获取分析师AI上下文
                        if use_analyst_context:
                            analyst_state = ra.db.get_state(symbol, timeframe)
                            if analyst_state:
                                from data.market_context import AnalystContext

                                analyst_ctx = AnalystContext.from_state(analyst_state)
                                if analyst_ctx:
                                    market_context.analyst_context = (
                                        analyst_ctx.to_dict()
                                    )

                        # 4. 调用AI进行风险分析
                        ai_analysis = ra.analyze_trade_risk(
                            symbol=symbol,
                            trade_plan=trade_plan,
                            risk_metrics=risk_metrics,
                            market_context=market_context,
                        )

                        # 5. 保存AI分析结果
                        risk_result = {
                            **risk_metrics,
                            "ai_risk_analysis": ai_analysis.get("full_analysis", ""),
                            "ai_recommendation": ai_analysis.get("recommendation", ""),
                            "risk_level": ai_analysis.get("risk_level", "MEDIUM"),
                        }

                        db.update_risk_analysis_result(analysis_id, risk_result)

                        # 6. 显示结果
                        st.success(f"✅ 风险分析完成 (ID: {analysis_id})")

                        # 风险等级标签
                        risk_level = risk_result.get("risk_level", "MEDIUM")
                        risk_colors = {
                            "LOW": "🟢",
                            "MEDIUM": "🟡",
                            "HIGH": "🟠",
                            "EXTREME": "🔴",
                        }
                        st.markdown(
                            f"### {risk_colors.get(risk_level, '⚪')} 风险等级: {risk_level}"
                        )

                        # 关键指标卡片
                        st.divider()

                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)

                        with col_r1:
                            st.metric(
                                "预期盈亏比 (R:R)",
                                f"1:{risk_metrics.get('risk_reward_expected', 0):.1f}",
                                delta=f"{risk_metrics.get('stop_distance_percent', 0):.2f}%止损",
                            )

                        with col_r2:
                            kelly = risk_metrics.get("kelly_fraction_adjusted", 0) * 100
                            st.metric(
                                "凯利建议仓位",
                                f"{kelly:.1f}%",
                                delta=f"保守系数0.8",
                                delta_color="normal",
                            )

                        with col_r3:
                            sharpe = risk_metrics.get("sharpe_ratio_estimate", 0)
                            st.metric(
                                "估计夏普比率",
                                f"{sharpe:.2f}",
                                delta=">1.0合格" if sharpe >= 1.0 else "<1.0偏低",
                                delta_color="green" if sharpe >= 1.0 else "orange",
                            )

                        with col_r4:
                            atr = risk_metrics.get("volatility_atr", 0)
                            st.metric(
                                "ATR波动率",
                                f"{atr:.2f}",
                                delta=f"{atr / entry_price * 100:.2f}%"
                                if entry_price > 0
                                else "",
                            )

                        # R-multiple计划
                        st.divider()
                        st.subheader("📐 R-Multiple 分批计划")

                        r_plan = risk_metrics.get("r_multiple_plan", {})

                        col_tp1, col_tp2, col_tp3 = st.columns(3)

                        with col_tp1:
                            st.info("**TP1: +1R**\n\n平仓 30%\n止损移至保本")

                        with col_tp2:
                            st.info("**TP2: +2R**\n\n平仓 30%\n止损移至+1R")

                        with col_tp3:
                            st.info("**TP3: +3R**\n\n平仓 40%\n或追踪止盈")

                        # Phase 5.2: ②类市场数据展示
                        st.divider()
                        st.subheader("📊 市场数据 (②类数据)")

                        # 获取市场上下文数据
                        market_ctx = None
                        if "market_context" in locals():
                            market_ctx = market_context

                        if market_ctx:
                            col_m1, col_m2, col_m3 = st.columns(3)

                            with col_m1:
                                # 资金费率
                                if (
                                    hasattr(market_ctx, "funding_rate")
                                    and market_ctx.funding_rate is not None
                                ):
                                    fr = market_ctx.funding_rate
                                    fr_color = "normal"
                                    fr_emoji = "🟢"
                                    if abs(fr) > 0.1:
                                        fr_color = "inverse"
                                        fr_emoji = "🔴"
                                    elif abs(fr) > 0.05:
                                        fr_color = "off"
                                        fr_emoji = "🟡"
                                    st.metric(
                                        f"{fr_emoji} 资金费率",
                                        f"{fr:.4f}%",
                                        delta="极端"
                                        if abs(fr) > 0.1
                                        else ("偏高" if abs(fr) > 0.05 else "正常"),
                                        delta_color=fr_color,
                                    )
                                else:
                                    st.metric("资金费率", "N/A")

                            with col_m2:
                                # 持仓量
                                if (
                                    hasattr(market_ctx, "open_interest")
                                    and market_ctx.open_interest is not None
                                ):
                                    oi = market_ctx.open_interest
                                    oi_change = getattr(
                                        market_ctx, "open_interest_change_24h", None
                                    )
                                    if oi_change is not None:
                                        st.metric(
                                            "📈 持仓量",
                                            f"{oi:,.0f}",
                                            delta=f"{oi_change:+.1f}%",
                                            delta_color="inverse"
                                            if abs(oi_change) > 30
                                            else "normal",
                                        )
                                    else:
                                        st.metric("持仓量", f"{oi:,.0f}")
                                else:
                                    st.metric("持仓量", "N/A")

                            with col_m3:
                                # 24h涨跌
                                if (
                                    hasattr(market_ctx, "price_change_24h")
                                    and market_ctx.price_change_24h is not None
                                ):
                                    pc = market_ctx.price_change_24h
                                    pc_emoji = "📈" if pc > 0 else "📉"
                                    st.metric(
                                        f"{pc_emoji} 24h涨跌",
                                        f"{pc:+.2f}%",
                                        delta=None,
                                    )
                                else:
                                    st.metric("24h涨跌", "N/A")

                            # 订单簿深度
                            col_m4, col_m5 = st.columns(2)
                            with col_m4:
                                if (
                                    hasattr(market_ctx, "spread_percent")
                                    and market_ctx.spread_percent is not None
                                ):
                                    sp = market_ctx.spread_percent
                                    st.metric(
                                        "买卖价差",
                                        f"{sp:.4f}%",
                                        delta="流动性良好"
                                        if sp < 0.05
                                        else ("注意滑点" if sp < 0.1 else "流动性差"),
                                        delta_color="normal"
                                        if sp < 0.05
                                        else ("off" if sp < 0.1 else "inverse"),
                                    )
                                else:
                                    st.metric("买卖价差", "N/A")

                            with col_m5:
                                if (
                                    hasattr(market_ctx, "mark_price")
                                    and market_ctx.mark_price is not None
                                ):
                                    mp = market_ctx.mark_price
                                    st.metric("标记价格", f"{mp:.2f}")
                                else:
                                    st.metric("标记价格", "N/A")

                            # 分析师上下文（如果有关联）
                            if (
                                hasattr(market_ctx, "analyst_context")
                                and market_ctx.analyst_context
                            ):
                                with st.expander("🔗 关联的分析师AI分析"):
                                    ctx = market_ctx.analyst_context
                                    if isinstance(ctx, dict):
                                        st.markdown(f"""
                                        - **市场周期**: {ctx.get("market_cycle", "N/A")}
                                        - **形态**: {ctx.get("pattern_name", "N/A")} ({ctx.get("pattern_status", "N/A")})
                                        - **置信度**: {ctx.get("confidence", 0):.0f}%
                                        - **趋势强度**: {ctx.get("trend_strength", "N/A")}
                                        """)
                                        if ctx.get("key_levels"):
                                            kl = ctx["key_levels"]
                                            st.markdown(f"""
                                            **建议价位**:
                                            - 入场: {kl.get("entry_trigger", "N/A")}
                                            - 止损: {kl.get("invalidation_level", "N/A")}
                                            - 目标: {kl.get("profit_target_1", "N/A")}
                                            """)
                        else:
                            st.info("暂无②类市场数据")

                        # AI建议
                        st.divider()
                        st.subheader("🤖 AI风险建议")

                        ai_rec = risk_result.get("ai_recommendation", "暂无建议")
                        st.info(ai_rec)

                        with st.expander("查看完整AI分析"):
                            st.markdown(
                                risk_result.get("ai_risk_analysis", "暂无详细分析")
                            )

                        # 仓位对比
                        st.divider()

                        suggested = risk_metrics.get("position_size_suggested", 0)
                        actual = position_size_actual

                        col_s1, col_s2 = st.columns(2)

                        with col_s1:
                            st.metric("AI建议仓位", f"{suggested:.1f}%")

                        with col_s2:
                            delta = actual - suggested
                            st.metric(
                                "您的计划仓位",
                                f"{actual:.1f}%",
                                delta=f"{delta:+.1f}% vs 建议",
                                delta_color="off"
                                if abs(delta) <= 2
                                else ("inverse" if delta > 0 else "normal"),
                            )

                        if actual > suggested * 1.5:
                            st.warning("⚠️ 您的计划仓位明显高于AI建议，请注意风险控制")

                    except Exception as e:
                        st.error(f"❌ 分析失败: {str(e)}")
                        import traceback

                        st.code(traceback.format_exc())
        else:
            # 初始状态提示
            st.info("👈 请在左侧输入您的交易计划，然后点击'AI风险分析'按钮")

            # 显示使用说明
            with st.expander("📖 使用说明"):
                st.markdown("""
                ### 如何使用风险计算器
                
                1. **输入交易计划**: 填写交易对、方向、入场价、止损价、目标位
                2. **估计胜率**: 根据您的价格行为分析，估计这笔交易的胜率
                3. **设置计划仓位**: 您打算使用的仓位比例
                4. **获取AI分析**: 系统会计算：
                   - 基于ATR的波动率评估
                   - 凯利公式最优仓位
                   - 夏普比率估计
                   - R-multiple分批止盈止损计划
                5. **对比建议**: 查看AI建议仓位与您的计划仓位差异
                
                ### R-Multiple 体系说明
                
                - **1R** = 止损距离（入场价 - 止损价）
                - **TP1 (+1R)**: 平30%，止损移至保本
                - **TP2 (+2R)**: 平30%，止损移至+1R锁定利润
                - **TP3 (+3R)**: 平40%或进入追踪止盈
                
                ### 凯利公式
                
                `f* = (p×b - q) / b`
                
                其中: p=胜率, q=败率=1-p, b=盈亏比
                
                系统使用保守系数0.8调整：`建议仓位 = f* × 0.8`
                """)

    # 历史记录区域
    st.divider()
    st.subheader("📚 风险分析历史")

    try:
        history = db.get_risk_analysis_history(limit=20)

        if history:
            # 转换为DataFrame显示
            df_data = []
            for record in history:
                df_data.append(
                    {
                        "ID": record.get("id"),
                        "时间": datetime.fromtimestamp(
                            record.get("created_at", 0) / 1000
                        ).strftime("%m-%d %H:%M"),
                        "交易对": record.get("symbol", "").replace(":USDT", ""),
                        "方向": record.get("direction", ""),
                        "入场价": f"{record.get('entry_price', 0):.2f}",
                        "止损价": f"{record.get('stop_loss', 0):.2f}",
                        "R:R": f"1:{record.get('risk_reward_expected', 0):.1f}",
                        "建议仓位": f"{record.get('position_size_suggested', 0):.1f}%",
                        "风险等级": record.get("risk_level", "MEDIUM"),
                        "状态": record.get("status", "ANALYZED"),
                    }
                )

            df = pd.DataFrame(df_data)

            # 添加颜色标记
            def color_risk_level(val):
                colors = {
                    "LOW": "background-color: #d4edda",
                    "MEDIUM": "background-color: #fff3cd",
                    "HIGH": "background-color: #f8d7da",
                    "EXTREME": "background-color: #f5c6cb",
                }
                return colors.get(val, "")

            st.dataframe(
                df.style.map(color_risk_level, subset=["风险等级"]),
                width="stretch",
                hide_index=True,
            )

            # 操作按钮
            col_op1, col_op2 = st.columns([1, 4])

            with col_op1:
                selected_id = st.number_input("选择记录ID", min_value=1, step=1)

            with col_op2:
                if selected_id > 0:
                    col_btn1, col_btn2 = st.columns(2)

                    with col_btn1:
                        if st.button("✅ 标记为已关闭", use_container_width=True):
                            db.close_risk_analysis(
                                int(selected_id), outcome_feedback="CLOSED"
                            )
                            st.rerun()

                    with col_btn2:
                        if st.button("🗑️ 删除记录", use_container_width=True):
                            # 软删除 - 标记为EXPIRED
                            db.expire_risk_analysis(int(selected_id))
                            st.rerun()
        else:
            st.info("暂无风险分析记录")

    except Exception as e:
        st.error(f"加载历史记录失败: {str(e)}")
