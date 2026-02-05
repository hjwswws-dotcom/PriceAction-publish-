"""
PriceAction 主入口模块
"""

import sys
import time
import threading
import sqlite3
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def init_database():
    """初始化数据库和表结构"""
    db_path = "./data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查 states 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='states'")
    table_exists = cursor.fetchone()

    if not table_exists:
        # 创建完整的表结构
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
                last_updated INTEGER
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_states_symbol ON states(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_states_timeframe ON states(timeframe)")

        conn.commit()
        print("[DB] 数据库已初始化，states 表就绪")

    conn.close()


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
    """保存单周期分析结果到数据库"""
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
        "last_updated": int(time.time() * 1000),
        "raw_response": full_result.get("raw_response", ""),
    }

    db._ensure_connection()
    cursor = db._conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO states
        (symbol, timeframe, marketCycle, activeNarrative, alternativeNarrative, analysis_text, actionPlan, last_updated, raw_response)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            state["symbol"],
            state["timeframe"],
            state["marketCycle"],
            state["activeNarrative"],
            state["alternativeNarrative"],
            state["analysis_text"],
            state["actionPlan"],
            state["last_updated"],
            state["raw_response"],
        ),
    )
    db._conn.commit()


def run_analysis_cycle(settings):
    """执行一次分析循环"""
    # 初始化数据库
    init_database()

    from database import DatabaseManager
    from src.data_provider.ccxt_fetcher import CCXTFetcher
    from src.llm.siliconflow_provider import SiliconFlowProvider
    import json

    db = DatabaseManager("./data.db")
    db._ensure_connection()

    # 数据库迁移：自动检查并补充所有缺失的列
    try:
        cursor = db._conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='states'")
        table_exists = cursor.fetchone()

        if table_exists:
            # 获取当前表的所有列
            cursor.execute("PRAGMA table_info(states)")
            columns = [row[1] for row in cursor.fetchall()]

            # 定义必需的列和默认值
            required_columns = {
                "actionPlan": "TEXT DEFAULT '{}'",
                "raw_response": "TEXT DEFAULT ''",
            }

            # 检查并添加缺失的列
            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    print(f"  [DB] 检测到缺少 {col_name} 列，执行迁移...")
                    cursor.execute(f"ALTER TABLE states ADD COLUMN {col_name} {col_def}")
                    db._conn.commit()
                    print(f"  [DB] {col_name} 列已添加")
        else:
            print("  [DB] states 表不存在，请确保已初始化数据库")

    except Exception as e:
        print(f"  [DB] 迁移检查跳过: {e}")

    # 获取配置
    symbols = settings.symbols
    timeframes = settings.timeframes
    api_key = settings.api_key

    # 初始化数据获取器和AI
    proxy = settings.proxy
    exchange_id = settings.exchange_id
    exchange_options = (
        json.loads(settings.exchange_options)
        if settings.exchange_options
        else {"defaultType": "swap"}
    )

    fetcher = CCXTFetcher(exchange_id=exchange_id, proxy=proxy, options=exchange_options)
    llm = SiliconFlowProvider(api_key=api_key)

    print(f"分析 {len(symbols)} 个交易对...")

    for symbol in symbols:
        print(f"正在分析 {symbol}...")

        try:
            # 1. 一次性获取所有周期的K线数据
            timeframe_data = {}
            for tf in ["15m", "1h", "1d"]:
                klines = fetcher.fetch_ohlcv(symbol, timeframe=tf, limit=50)
                if klines:
                    timeframe_data[tf] = klines
                    print(f"  获取 {tf} K线: {len(klines)} 根")

            if not timeframe_data:
                print(f"  [ERROR] {symbol}: 无法获取任何K线数据")
                continue

            # 2. 获取各周期当前状态
            current_states = {}
            for tf in timeframe_data.keys():
                state = db.get_state(symbol, tf)
                current_states[tf] = state

            # 3. 调用多周期AI分析（一次性分析所有周期）
            print(f"  调用多周期分析...")
            result = llm.analyze_multi_timeframe(symbol, timeframe_data, current_states)

            if not result.get("success"):
                print(f"  [ERROR] {symbol}: AI分析失败 - {result.get('error', '未知错误')}")
                # 降级：尝试单周期分析
                for tf, klines in timeframe_data.items():
                    _analyze_single_timeframe(symbol, tf, klines, db, llm)
                continue

            # 4. 解析多周期结果
            from src.core.response_parser import ResponseParser

            parse_result = ResponseParser().parse_multi_timeframe(result.get("raw_response", ""))

            if not parse_result.get("success"):
                print(f"  [WARNING] {symbol}: 多周期解析失败，尝试降级")
                for tf, klines in timeframe_data.items():
                    _analyze_single_timeframe(symbol, tf, klines, db, llm)
                continue

            # 5. 保存每个周期的分析结果
            timeframe_states = parse_result.get("timeframe_states", {})
            for tf in timeframe_data.keys():
                if tf in timeframe_states:
                    _save_timeframe_state(symbol, tf, timeframe_states[tf], db, result)
                    # 获取该周期最新价格
                    current_price = (
                        timeframe_data[tf][-1].get("close", 0) if timeframe_data[tf] else 0
                    )
                    print(f"  [OK] {symbol} {tf} @ {current_price:.2f}")
                else:
                    # 该周期没有分析结果，单周期分析
                    _analyze_single_timeframe(symbol, tf, timeframe_data[tf], db, llm)

            print(f"  {symbol} 多周期分析完成")

        except Exception as e:
            print(f"  [ERROR] {symbol}: {e}")
            import traceback

            traceback.print_exc()

    db.close()
    print("分析完成")


def run_backend():
    """启动后端分析服务"""
    from src.config.settings import get_settings

    try:
        settings = get_settings()
    except Exception as e:
        print(f"[ERROR] 配置加载失败: {e}")
        return

    print("=" * 50)
    print("PriceAction Backend Service")
    print("=" * 50)
    print(f"Environment: {settings.environment}")
    print(f"Log Level: {settings.log_level}")
    print(f"Monitored Symbols: {', '.join(settings.symbols)}")
    print(f"Timeframes: {', '.join(settings.timeframes)}")
    print(f"K-lines Limit: {settings.analysis_klines_limit}")
    print(f"Exchange: {settings.exchange_id}")
    print(f"Proxy: {settings.proxy or 'None'}")
    print("=" * 50)
    print("")

    # 执行初始分析
    print("执行初始分析...")
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
        while True:
            # 每15分钟执行一次分析
            time.sleep(900)  # 15分钟 = 900秒

            print("")
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行定时分析...")
            try:
                run_analysis_cycle(settings)
            except Exception as e:
                print(f"[ERROR] 定时分析失败: {e}")

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

    parser = argparse.ArgumentParser(description="PriceAction - AI Price Action Analyzer")
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
