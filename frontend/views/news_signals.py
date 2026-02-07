"""
新闻面板页面 (News Panel)
展示最新捕捉到的新闻
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import json

# 页面配置
st.set_page_config(page_title="📰 新闻面板 | AI价格行为分析", page_icon="📰", layout="wide")

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


def display_news_card(news: Dict):
    """显示新闻卡片"""
    title = news.get("title", "无标题")
    source = news.get("source", "未知来源")
    published_time = format_timestamp(news.get("published_time_utc", 0))
    url = news.get("url", "")
    votes_positive = news.get("votes_positive", 0)
    votes_negative = news.get("votes_negative", 0)

    # 情绪判断
    sentiment = "😐 中性"
    if votes_positive > votes_negative * 2:
        sentiment = "🟢 利好"
    elif votes_negative > votes_positive * 2:
        sentiment = "🔴 利空"

    # 构建卡片
    with st.container():
        st.markdown(
            f"""
        <div style="
            border-left: 4px solid #4a90d9;
            background-color: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        ">
            <h4 style="margin: 0 0 8px 0; color: #1a1a1a;">
                {title}
            </h4>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">
                <strong>来源:</strong> {source} |
                <strong>时间:</strong> {published_time} |
                <strong>情绪:</strong> {sentiment}
            </p>
            <p style="margin: 5px 0; font-size: 12px; color: #999;">
                👍 {votes_positive} | 👎 {votes_negative}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 展开显示详情和原文链接
        if url:
            with st.expander("查看详情"):
                st.markdown(f"**原文链接**: [{url}]({url})")


def display_refined_doc_card(doc: Dict):
    """显示已提纯的新闻文档"""
    title = doc.get("title", "无标题")
    summary = doc.get("summary", "") or doc.get("text_content", "")[:500]
    created_at = format_timestamp(doc.get("created_at", 0))
    extract_method = doc.get("extract_method", "unknown")

    with st.container():
        st.markdown(
            f"""
        <div style="
            border-left: 4px solid #28a745;
            background-color: #f0fff4;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        ">
            <h4 style="margin: 0 0 8px 0; color: #1a1a1a;">
                📄 {title}
            </h4>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">
                <strong>提纯时间:</strong> {created_at} |
                <strong>方法:</strong> {extract_method}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 展开显示摘要
        with st.expander("查看提纯内容"):
            st.markdown(summary)


def main():
    """主函数"""
    st.title("📰 新闻面板")
    st.markdown("实时监控加密货币相关新闻")
    st.markdown("---")

    # 初始化数据库
    try:
        import os

        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data.db"
        )
        db = DatabaseManager(db_path)
        db._ensure_connection()
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return

    # 侧边栏筛选
    st.sidebar.header("筛选条件")

    # 时间范围筛选
    time_range = st.sidebar.selectbox(
        "时间范围", options=["最近24小时", "最近7天", "全部"], index=0
    )

    # 转换时间范围为小时
    hours_map = {"最近24小时": 24, "最近7天": 168, "全部": 0}
    hours = hours_map.get(time_range, 24)

    # 自动刷新
    auto_refresh = st.sidebar.checkbox("自动刷新 (60秒)", value=False)
    if auto_refresh:
        st.sidebar.info("页面将每60秒自动刷新")
        st.empty()

    # 获取新闻数据
    try:
        recent_news = db.get_recent_news_items(limit=50)

        # 按时间过滤
        from datetime import datetime, timedelta

        if hours > 0:
            cutoff_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
            recent_news = [
                n for n in recent_news if (n.get("published_time_utc") or 0) >= cutoff_time
            ]

        # 显示统计信息
        st.sidebar.metric("新闻总数", len(recent_news))

    except Exception as e:
        st.error(f"获取新闻数据失败: {e}")
        import traceback

        st.error(traceback.format_exc())
        recent_news = []

    # 主界面：显示新闻列表
    st.header("最新新闻")

    if recent_news:
        for news in recent_news[:20]:  # 只显示前20条
            display_news_card(news)
    else:
        st.info("暂无新闻数据")

    # 展开显示已提纯的文档
    st.markdown("---")
    st.header("📄 已提纯的新闻")

    try:
        refined_docs = db.get_refined_docs_for_analysis(limit=10)

        if refined_docs:
            for doc in refined_docs:
                display_refined_doc_card(doc)
        else:
            st.info("暂无已提纯的新闻文档")
    except Exception as e:
        st.warning(f"获取提纯文档失败: {e}")

    # 底部说明
    st.markdown("---")
    st.markdown("""
    **说明:**
    - 显示最近抓取的新闻及其情绪投票
    - 已提纯的新闻显示AI提取的摘要内容
    - 新闻每30分钟自动更新
    """)

    st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
