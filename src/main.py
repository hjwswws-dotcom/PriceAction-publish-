"""
PriceAction 主入口模块
"""

import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def run_backend():
    """启动后端分析服务"""
    from src.config.settings import get_settings
    from src.utils.logger import logger

    settings = get_settings()
    logger.info(f"Starting PriceAction Backend v2.0.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log Level: {settings.log_level}")

    # TODO: Implement backend
    print("Backend service starting...")


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

    parser = argparse.ArgumentParser(
        description="PriceAction - AI Price Action Analyzer"
    )
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
