"""
Pydantic Settings 配置管理
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_env_file():
    """加载.env文件到环境变量"""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


# 加载环境变量
_load_env_file()


class Settings(BaseSettings):
    """主配置类"""

    # 核心配置
    environment: str = "development"
    log_level: str = "INFO"

    # 交易所配置
    exchange_id: str = "binance"
    exchange_proxy: Optional[str] = None
    exchange_options: str = '{"defaultType": "swap"}'

    # LLM配置
    llm_provider: str = "siliconflow"
    llm_siliconflow_api_key: Optional[str] = None
    llm_nvidia_api_key: Optional[str] = None
    llm_model: str = "Pro/deepseek-ai/DeepSeek-V3.2"
    llm_max_tokens: int = 8192
    llm_temperature: float = 0.7
    llm_max_retries: int = 3

    # 分析配置
    analysis_symbols: List[str] = [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
        "XAU/USDT:USDT",
        "XAG/USDT:USDT",
    ]
    analysis_timeframes: List[str] = ["15m", "1h", "1d"]
    analysis_klines_limit: int = 50

    # 多周期配置
    multi_timeframe_enabled: bool = True
    multi_timeframe_consensus_threshold: float = 0.7

    # 数据库配置
    database_path: str = "./data.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PRICEACTION_",
        extra="ignore",
    )

    @property
    def proxy(self) -> Optional[str]:
        """获取代理配置"""
        return self.exchange_proxy

    @property
    def symbols(self) -> List[str]:
        """获取交易对列表"""
        return self.analysis_symbols

    @property
    def timeframes(self) -> List[str]:
        """获取时间框架列表"""
        return self.analysis_timeframes

    @property
    def api_key(self) -> str:
        """获取当前LLM提供商的API密钥"""
        if self.llm_provider == "siliconflow":
            return self.llm_siliconflow_api_key or os.getenv("SILICONFLOW_API_KEY", "")
        elif self.llm_provider == "nvidia":
            return self.llm_nvidia_api_key or os.getenv("NVIDIA_API_KEY", "")
        return ""


# 全局Settings实例
_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """获取全局Settings实例"""
    global _settings
    if reload or _settings is None:
        _settings = Settings()
    return _settings
