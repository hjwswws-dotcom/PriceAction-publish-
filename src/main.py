"""
PriceAction 主入口模块 - 异步架构版本
支持并发数据获取和多周期共振分析
"""

import sys
import time
import threading
import sqlite3
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加src目录到路径
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 并发保护锁 - 防止分析循环重叠执行
_analysis_lock = threading.Lock()

# 新闻抓取模块导入
from src.data.news.cryptocompare_scraper import CryptoCompareScraper
from src.data.news.refiner import Refiner
from src.data.news.analyzer import NewsAnalyzer


def init_database():
    """初始化数据库和表结构"""
    db_path = "./data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 🔧 强制重置：检查并删除所有旧表，确保 schema 绝对正确
    tables_to_reset = [
        "states",
        "news_items",
        "refined_docs",
        "news_signals",
        "trading_signals",
        "trades",
    ]
    for table in tables_to_reset:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"[DB] 已删除旧表: {table}")

    # 🔧 强制重建：创建完整的 states 表结构
    cursor.execute("""
        CREATE TABLE states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timeframe TEXT,
            timestamp INTEGER,
            marketCycle TEXT,
            marketStructure TEXT,
            signalConfidence INTEGER,
            activeNarrative TEXT,
            alternativeNarrative TEXT,
            actionPlan TEXT,
            volumeProfile TEXT,
            keyLevels TEXT,
            analysis_text TEXT,
            raw_response TEXT,
            consensus_score REAL,
            consensus_direction TEXT,
            last_updated INTEGER
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_states_symbol ON states(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_states_timeframe ON states(timeframe)")

    # 🔧 强制重建：创建完整的 news_items 表
    cursor.execute("""
        CREATE TABLE news_items (
            id TEXT PRIMARY KEY,
            source TEXT,
            source_item_id TEXT,
            title TEXT,
            url TEXT,
            published_time_utc INTEGER,
            ingest_time_utc INTEGER,
            content TEXT,
            language TEXT,
            votes_positive INTEGER DEFAULT 0,
            votes_negative INTEGER DEFAULT 0,
            votes_installed INTEGER DEFAULT 0,
            domain TEXT,
            kind TEXT,
            status TEXT DEFAULT 'NEW',
            created_at INTEGER,
            updated_at INTEGER
        )
    """)

    # 🔧 强制重建：创建完整的 refined_docs 表
    cursor.execute("""
        CREATE TABLE refined_docs (
            id TEXT PRIMARY KEY,
            news_id TEXT,
            url TEXT,
            title TEXT,
            markdown_content TEXT,
            summary TEXT,
            key_entities TEXT,
            quotes TEXT,
            status TEXT,
            error_message TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
    """)

    # 🔧 强制重建：创建完整的 news_signals 表（包含 severity 字段）
    cursor.execute("""
        CREATE TABLE news_signals (
            signal_id TEXT PRIMARY KEY,
            event_type TEXT,
            one_line_thesis TEXT,
            assets TEXT,
            direction TEXT,
            confidence INTEGER,
            timeframe TEXT,
            impact_volatility INTEGER,
            tail_risk INTEGER,
            news_ids TEXT,
            evidence_urls TEXT,
            is_active INTEGER DEFAULT 1,
            created_time_utc INTEGER,
            expires_time_utc INTEGER,
            severity TEXT DEFAULT 'INFO'
        )
    """)

    # 🔧 强制重建：创建 trading_signals 表
    cursor.execute("""
        CREATE TABLE trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timeframe TEXT,
            timestamp INTEGER,
            signal_type TEXT,
            direction TEXT,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            confidence INTEGER,
            pattern_name TEXT,
            signal_checks TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at INTEGER,
            updated_at INTEGER
        )
    """)

    # 🔧 强制重建：创建 trades 表
    cursor.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timeframe TEXT,
            direction TEXT,
            status TEXT DEFAULT 'ANALYZED',
            entry_price REAL,
            stop_loss REAL,
            take_profit_1 REAL,
            take_profit_2 REAL,
            win_probability REAL,
            position_size_actual REAL,
            position_size_suggested REAL,
            risk_amount_percent REAL,
            risk_reward_expected REAL,
            volatility_atr REAL,
            volatility_atr_15m REAL,
            volatility_atr_1h REAL,
            volatility_atr_1d REAL,
            sharpe_ratio_estimate REAL,
            kelly_fraction REAL,
            kelly_fraction_adjusted REAL,
            max_drawdown_estimate REAL,
            r_multiple_plan TEXT,
            stop_distance_percent REAL,
            ai_risk_analysis TEXT,
            ai_recommendation TEXT,
            risk_level TEXT,
            analysis_timestamp INTEGER,
            user_notes TEXT,
            outcome_feedback TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
    """)

    conn.commit()
    print("[DB] 数据库已强制重置，所有表已重建")

    conn.close()


def _save_consolidated_state(
    symbol: str,
    timeframe_states: Dict[str, Dict],
    consensus: Dict,
    db,
    raw_response: str = "",
    analysis_text: str = "",
):
    """保存统一的分析状态到数据库（包含共振信息）"""
    import time as time_module

    for tf, state in timeframe_states.items():
        db_state = {
            "symbol": symbol,
            "timeframe": tf,
            "marketCycle": state.get("marketCycle", "TRADING_RANGE"),
            "activeNarrative": json.dumps(state.get("activeNarrative", {}), ensure_ascii=False),
            "alternativeNarrative": json.dumps(
                state.get("alternativeNarrative", {}), ensure_ascii=False
            ),
            "analysis_text": analysis_text,  # 🔧 移除 tf == "15m" 的判断，全周期保存
            "actionPlan": json.dumps(state.get("actionPlan", {}), ensure_ascii=False),
            "consensus_score": consensus.get("confidence", 0.0),
            "consensus_direction": consensus.get("direction", "NEUTRAL"),
            "last_updated": int(time_module.time() * 1000),  # 保存 UTC 时间戳，前端负责时区转换
            "raw_response": raw_response,  # 🔧 全周期保存原始响应，不做过滤
        }

        db._ensure_connection()
        cursor = db._conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO states
            (symbol, timeframe, marketCycle, activeNarrative, alternativeNarrative, 
             analysis_text, actionPlan, consensus_score, consensus_direction, last_updated, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                db_state["symbol"],
                db_state["timeframe"],
                db_state["marketCycle"],
                db_state["activeNarrative"],
                db_state["alternativeNarrative"],
                db_state["analysis_text"],
                db_state["actionPlan"],
                db_state["consensus_score"],
                db_state["consensus_direction"],
                db_state["last_updated"],
                db_state["raw_response"],
            ),
        )
        db._conn.commit()


def _analyze_single_timeframe(symbol, tf, klines, db, llm):
    """单周期降级分析"""
    try:
        current_state = db.get_state(symbol, tf)
        result = llm.analyze(symbol, klines, current_state)

        if result and result.get("success"):
            _save_timeframe_state(symbol, tf, result, db, result)
            current_price = klines[-1].get("close", 0) if klines else 0
            print(f"  [OK] {symbol} {tf} @ {current_price:.2f} (降级)")
        else:
            print(f"  [ERROR] {symbol} {tf}: 单周期分析也失败")
    except Exception as e:
        print(f"  [ERROR] {symbol} {tf}: {e}")


def _save_timeframe_state(symbol, tf, result, db, full_result):
    """保存单周期分析结果到数据库（降级时使用）"""
    import json
    import time

    state = {
        "symbol": symbol,
        "timeframe": tf,
        "marketCycle": result.get("marketCycle", "TRADING_RANGE"),
        "activeNarrative": json.dumps(result.get("activeNarrative", {}), ensure_ascii=False),
        "alternativeNarrative": json.dumps(
            result.get("alternativeNarrative", {}), ensure_ascii=False
        ),
        "analysis_text": full_result.get("analysis_text", ""),
        "actionPlan": json.dumps(result.get("actionPlan", {}), ensure_ascii=False),
        "consensus_score": 0.0,
        "consensus_direction": "NEUTRAL",
        "last_updated": int(time.time() * 1000),
        "raw_response": full_result.get("raw_response", ""),
    }

    db._ensure_connection()
    cursor = db._conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO states
        (symbol, timeframe, marketCycle, activeNarrative, alternativeNarrative, 
         analysis_text, actionPlan, consensus_score, consensus_direction, last_updated, raw_response)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            state["symbol"],
            state["timeframe"],
            state["marketCycle"],
            state["activeNarrative"],
            state["alternativeNarrative"],
            state["analysis_text"],
            state["actionPlan"],
            state["consensus_score"],
            state["consensus_direction"],
            state["last_updated"],
            state["raw_response"],
        ),
    )
    db._conn.commit()


async def process_symbol_async(
    symbol: str, timeframes: List[str], fetcher, llm, db, consensus_calc
) -> bool:
    """
    异步处理单个交易对的多周期分析

    Args:
        symbol: 交易对符号
        timeframes: 时间框架列表
        fetcher: 异步数据获取器
        llm: LLM Provider
        db: 数据库管理器
        consensus_calc: 共振计算器

    Returns:
        是否成功
    """
    print(f"正在分析 {symbol}...")

    try:
        # 1. 并发获取所有周期的K线数据
        print(f"  并发获取 {len(timeframes)} 个周期数据...")
        timeframe_data = await fetcher.fetch_all_timeframes(symbol, timeframes, limit=50)

        valid_timeframes = {tf: data for tf, data in timeframe_data.items() if data}
        if not valid_timeframes:
            print(f"  [ERROR] {symbol}: 无法获取任何K线数据")
            return False

        for tf, data in valid_timeframes.items():
            print(f"  ✓ {tf}: {len(data)} 根K线")

        # 2. 获取各周期当前状态
        current_states = {}
        for tf in valid_timeframes.keys():
            current_states[tf] = db.get_state(symbol, tf)

        # 获取新闻上下文（如果存在）
        news_context = None
        recent_signals = db.get_latest_news_signals(limit=5)
        if recent_signals:
            news_context = {
                "items": recent_signals,
                "risk_summary": {"level": "NORMAL" if not recent_signals else "CAUTION"},
            }

        # 3. 调用多周期AI分析（传入RAG和新闻）
        print(f"  调用多周期AI分析...")
        result = llm.analyze_multi_timeframe(
            symbol,
            valid_timeframes,
            current_states,
            rag_context="",  # 暂时为空，后续可集成RAG
            news_context=news_context,
        )

        if not result.get("success"):
            print(f"  [ERROR] {symbol}: AI分析失败 - {result.get('error', '未知错误')}")
            # 降级：尝试单周期分析
            for tf, klines in valid_timeframes.items():
                _analyze_single_timeframe(symbol, tf, klines, db, llm)
            return False

        # 4. 解析多周期结果
        from src.core.response_parser import ResponseParser

        parse_result = ResponseParser().parse_multi_timeframe(result.get("raw_response", ""))

        if not parse_result.get("success"):
            print(f"  [WARNING] {symbol}: 多周期解析失败，尝试降级")
            for tf, klines in valid_timeframes.items():
                _analyze_single_timeframe(symbol, tf, klines, db, llm)
            return False

        # 5. 提取各周期状态
        timeframe_states = parse_result.get("timeframe_states", {})

        # 6. 计算共振分数（关键改进！）
        states_for_consensus = []
        for tf, state in timeframe_states.items():
            state_copy = state.copy()
            state_copy["symbol"] = symbol
            state_copy["timeframe"] = tf
            states_for_consensus.append(state_copy)

        consensus = consensus_calc.calculate_consensus(states_for_consensus)
        print(f"  共振分析: {consensus['direction']} (置信度: {consensus['confidence']:.0%})")

        # 7. 一次性保存所有周期的状态和共振信息
        _save_consolidated_state(
            symbol,
            timeframe_states,
            consensus,
            db,
            raw_response=result.get("raw_response", ""),
            analysis_text=parse_result.get("analysis_text", ""),
        )

        # 8. 输出结果摘要
        for tf in valid_timeframes.keys():
            if tf in timeframe_states:
                current_price = valid_timeframes[tf][-1].get("close", 0)
                print(f"  [OK] {symbol} {tf} @ {current_price:.2f}")

        print(f"  {symbol} 多周期分析完成 (共振: {consensus['recommendation']})")
        return True

    except Exception as e:
        print(f"  [ERROR] {symbol}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_analysis_cycle_async(settings):
    """
    执行异步分析循环

    Args:
        settings: 配置对象
    """
    # 初始化数据库
    init_database()

    from database import DatabaseManager
    from src.data_provider.async_ccxt_fetcher import AsyncCCXTFetcher
    from src.llm.siliconflow_provider import SiliconFlowProvider
    from src.core.consensus_calculator import ConsensusCalculator

    db = DatabaseManager("./data.db")
    db._ensure_connection()

    # 获取配置
    symbols = settings.symbols
    timeframes = settings.timeframes
    api_key = settings.api_key

    # 初始化组件
    proxy = settings.proxy
    exchange_id = settings.exchange_id
    exchange_options = (
        json.loads(settings.exchange_options)
        if settings.exchange_options
        else {"defaultType": "swap"}
    )

    # 初始化共振计算器（权重：日线最高，小时次之，15分钟最低）
    consensus_weights = {"15m": 0.3, "1h": 0.6, "1d": 1.0}
    consensus_calc = ConsensusCalculator(consensus_weights)

    # 初始化LLM
    llm = SiliconFlowProvider(api_key=api_key)

    print(f"分析 {len(symbols)} 个交易对...")

    # 使用异步上下文管理器管理fetcher生命周期
    async with AsyncCCXTFetcher(
        exchange_id=exchange_id, proxy=proxy, options=exchange_options
    ) as fetcher:
        # 顺序处理每个币种（避免API限流），但每个币种内部并发获取多周期数据
        for symbol in symbols:
            await process_symbol_async(
                symbol=symbol,
                timeframes=timeframes,
                fetcher=fetcher,
                llm=llm,
                db=db,
                consensus_calc=consensus_calc,
            )

    db.close()
    print("分析完成")


def run_analysis_cycle(settings):
    """同步包装器 - 运异步分析循环"""
    asyncio.run(run_analysis_cycle_async(settings))


def run_news_pipeline(db, proxy):
    """执行新闻抓取和处理流水线"""
    try:
        print("[News] 开始新闻抓取...")

        # 1. 抓取新闻
        scraper = CryptoCompareScraper(db, proxy=proxy)
        news_items = scraper.fetch(limit=10)

        for item in news_items:
            db.save_news_item(item)

        print(f"[News] 抓取了 {len(news_items)} 条新闻")

        # 2. 提纯内容
        refiner = Refiner(db)
        refined_count = 0

        recent_news = db.get_recent_news_items(limit=10)
        for news_item in recent_news:
            if news_item.get("status") == "NEW":
                refined = refiner.refine(news_item["id"], news_item["url"])
                if refined:
                    db.save_refined_doc(refined)
                    refined_count += 1

        print(f"[News] 提纯了 {refined_count} 条文档")

        # 3. 分析事件
        analyzer = NewsAnalyzer(db)
        signal_count = 0

        for doc in recent_news:
            if doc.get("status") == "COMPLETED":
                signal = analyzer.extract_signals(doc)
                if signal:
                    db.save_news_signal(signal)
                    signal_count += 1

        print(f"[News] 提取了 {signal_count} 个信号")

        # 4. 清理过期信号
        db.deactivate_expired_signals()

        print("[News] 新闻流水线完成")

    except Exception as e:
        print(f"[News Error] 新闻流水线失败: {e}")
        import traceback

        traceback.print_exc()


def run_backend():
    """启动后端分析服务"""
    # ✅ 步骤 0: 最先初始化数据库（建表/重置表结构），在任何其他逻辑之前
    init_database()

    from src.config.settings import get_settings

    try:
        settings = get_settings()
    except Exception as e:
        print(f"[ERROR] 配置加载失败: {e}")
        return

    print("=" * 50)
    print("PriceAction Backend Service (Async Architecture)")
    print("=" * 50)

    # ✅ 步骤 1: 执行首次新闻抓取（此时表已经存在，不再报错）
    print("\n[Step 1] 执行首次新闻抓取...")
    try:
        from database import DatabaseManager

        db = DatabaseManager("./data.db")
        run_news_pipeline(db, settings.proxy)
        db.close()
        print("首次新闻抓取完成")
    except Exception as e:
        print(f"[WARNING] 首次新闻抓取失败: {e}")

    # ✅ 步骤 2: 执行市场初始分析
    print("\n[Step 2] 执行初始市场分析...")
    try:
        run_analysis_cycle(settings)
    except Exception as e:
        print(f"[ERROR] 初始分析失败: {e}")
        import traceback

        traceback.print_exc()

    print("")
    print("后端服务运行中 (按 Ctrl+C 停止)")
    print("")

    try:
        news_counter = 0

        while True:
            time.sleep(900)  # 15分钟 = 900秒

            # 并发保护：防止上一轮分析未完成时启动新一轮
            if not _analysis_lock.acquire(blocking=False):
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [SKIP] 上一轮分析仍在进行中")
                continue

            try:
                print("")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行定时分析...")
                try:
                    run_analysis_cycle(settings)
                except Exception as e:
                    print(f"[ERROR] 定时分析失败: {e}")

                # 每2个周期（30分钟）执行一次新闻抓取
                news_counter += 1
                if news_counter >= 2:
                    news_counter = 0
                    from database import DatabaseManager

                    db = DatabaseManager("./data.db")
                    run_news_pipeline(db, settings.proxy)
                    db.close()
            finally:
                _analysis_lock.release()  # 确保释放锁

    except KeyboardInterrupt:
        print("\n正在停止后端服务...")
        print("后端服务已停止")


def run_frontend():
    """启动前端界面"""
    import streamlit.web.cli

    streamlit.web.cli.main_run(
        [
            "frontend/app.py",
            "--server.port",
            "8501",
            "--browser.gatherUsageStats",
            "false",
        ]
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PriceAction - AI Price Action Analyzer (Async)")
    parser.add_argument(
        "--mode",
        choices=["backend", "frontend", "both"],
        default="both",
        help="运行模式: backend=后端, frontend=前端, both=两者",
    )

    args = parser.parse_args()

    if args.mode in ["backend", "both"]:
        run_backend()

    if args.mode in ["frontend", "both"]:
        run_frontend()
