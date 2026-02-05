"""
Streamlit前端应用 - 双页结构
页1: 详细分析 | 页2: 快速概览
"""

import streamlit as st
import sys
from pathlib import Path

# 添加项目根目录和frontend目录到Python路径
project_root = Path(__file__).parent.parent
frontend_dir = Path(__file__).parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(frontend_dir) not in sys.path:
    sys.path.insert(0, str(frontend_dir))

# 导入页面模块
from frontend.views import detailed_analysis, quick_overview

# 页面配置
st.set_page_config(
    page_title="AI价格行为分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown(
    """
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .bull-trend { color: #26a69a; }
    .bear-trend { color: #ef5350; }
    .trading-range { color: #ff9800; }
</style>
""",
    unsafe_allow_html=True,
)


def main():
    """主函数 - 侧边栏导航"""
    # 导航状态初始化
    if "nav_choice" not in st.session_state:
        st.session_state.nav_choice = "📊 详细分析"

    # 页面标题
    st.markdown('<div class="main-header">📊 AI价格行为分析系统</div>', unsafe_allow_html=True)

    # 侧边栏导航
    with st.sidebar:
        st.header("导航")

        page = st.radio(
            "选择页面:",
            [
                "📊 详细分析",
                "📋 快速概览",
                "🚨 交易信号",
                "🎯 风险计算器",
                "📰 新闻信号",
            ],
            index=0,
            key="main_nav_radio",
            help="详细分析: AI完整分析 | 快速概览: 状态表格 | 交易信号: 推荐/警告信号 | 风险计算器: AI风险评估 | 新闻信号: 实时新闻警报",
        )

        st.divider()

        # 缓存清理提示
        st.subheader("🧹 缓存清理")
        st.info(
            "由于架构变更，建议点击右上角 **Clear cache** 清理旧缓存数据，以确保显示最新分析结果。"
        )

        if st.button("🧹 清理所有缓存"):
            st.cache_data.clear()
            st.success("缓存已清理！请刷新页面。")
            st.rerun()

        st.divider()

        # 系统信息
        st.subheader("📋 系统信息")
        st.write("- 监控币种: BTC, ETH, XAG, XAU")
        st.write("- 时间框架: 15m/1h/1d")
        st.write("- 分析间隔: 15分钟")
        st.write("- AI模型: DeepSeek-V3.2")

        st.divider()

        # 刷新按钮
        if st.button("🔄 刷新数据", width="stretch"):
            st.rerun()

    # 根据选择显示不同页面
    if page == "📊 详细分析":
        detailed_analysis.show()
    elif page == "📋 快速概览":
        quick_overview.show()
    elif page == "🚨 交易信号":
        # 信号面板页面 - 使用相对路径
        import frontend.views.signals as signals_page

        signals_page.main()
    elif page == "🎯 风险计算器":
        # 风险计算器页面
        import frontend.views.risk_calculator as risk_page

        risk_page.show()
    elif page == "📰 新闻信号":
        # 新闻信号页面
        import frontend.views.news_signals as news_page

        news_page.main()

    # 页脚
    st.divider()
    st.caption(
        "AI Price Action Analyzer v1.3.0 | Intelligent Signal System | Powered by DeepSeek-V3.2"
    )


if __name__ == "__main__":
    main()
