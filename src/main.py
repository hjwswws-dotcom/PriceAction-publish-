"""
PriceAction 主入口模块
"""

import sys
import time
import threading
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def run_analysis_cycle(settings):
    """执行一次分析循环"""
    from src.config.settings import get_settings
    from database import DatabaseManager
    import json
    import time as time_module

    db = DatabaseManager("./data.db")

    # 获取配置
    symbols = settings.analysis.symbols
    timeframes = settings.analysis.timeframes

    print(f"分析 {len(symbols)} 个交易对...")

    for symbol in symbols:
        for tf in timeframes:
            try:
                # 模拟价格数据（避免网络请求）
                import random

                base_price = 50000 if "BTC" in symbol else 3000
                current_price = base_price * (1 + random.uniform(-0.02, 0.02))

                # 构建简单的分析状态
                state = {
                    "symbol": symbol,
                    "timeframe": tf,
                    "marketCycle": "TRADING_RANGE",
                    "activeNarrative": json.dumps(
                        {
                            "pattern_name": "Range Bound",
                            "status": "IN_PROGRESS",
                            "key_levels": {
                                "entry_trigger": round(current_price, 2),
                                "invalidation_level": round(current_price * 0.99, 2),
                                "profit_target_1": round(current_price * 1.02, 2),
                            },
                            "probability": "MEDIUM",
                            "probability_value": 50.0,
                            "risk_reward": 2.0,
                        }
                    ),
                    "alternativeNarrative": json.dumps(
                        {
                            "pattern_name": "Breakout",
                            "trigger_condition": "突破阻力位",
                        }
                    ),
                    "analysis_text": f"价格行为分析 - {symbol} {tf}\n当前价格: {round(current_price, 2)} USDT\n市场状态: 震荡整理",
                    "last_updated": int(time_module.time() * 1000),
                }

                # 保存到数据库
                try:
                    cursor = db._conn.cursor()
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO states
                        (symbol, timeframe, marketCycle, activeNarrative, alternativeNarrative, analysis_text, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            state["symbol"],
                            state["timeframe"],
                            state["marketCycle"],
                            state["activeNarrative"],
                            state["alternativeNarrative"],
                            state["analysis_text"],
                            state["last_updated"],
                        ),
                    )
                    db._conn.commit()
                    print(f"  [OK] {symbol} {tf} @ {round(current_price, 2)}")
                except Exception as e:
                    print(f"  [ERROR] {symbol} {tf}: {e}")

            except Exception as e:
                print(f"  [ERROR] {symbol} {tf}: {e}")

    db.close()
    print("分析完成")


def run_backend():
    """启动后端分析服务"""
    from src.config.settings import get_settings
    from src.utils.logger import logger

    settings = get_settings()
    logger.info(f"Starting PriceAction Backend v2.0.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log Level: {settings.log_level}")

    print("=" * 50)
    print("PriceAction Backend Service")
    print("=" * 50)
    print(f"Monitored Symbols: {', '.join(settings.analysis.symbols)}")
    print(f"Timeframes: {', '.join(settings.analysis.timeframes)}")
    print(f"K-lines Limit: {settings.analysis.klines_limit}")
    print("=" * 50)
    print("")

    # 执行初始分析
    print("执行初始分析...")
    run_analysis_cycle(settings)

    print("")
    print("后端服务运行中 (按 Ctrl+C 停止)")
    print("")

    try:
        while True:
            # 每15分钟执行一次分析
            time.sleep(900)  # 15分钟 = 900秒

            print("")
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行定时分析...")
            run_analysis_cycle(settings)

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
        help="启动模式: backend=后端, frontend=前端, both=两者",
    )

    args = parser.parse_args()

    if args.mode in ["backend", "both"]:
        run_backend()

    if args.mode in ["frontend", "both"]:
        run_frontend()
