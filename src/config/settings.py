"""
Pydantic Settings 配置管理
"""

import os
from typing import Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM提供商配置"""

    provider: str = "siliconflow"
    siliconflow_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    model: str = "Pro/deepseek-ai/DeepSeek-V3.2"
    max_tokens: int = 8192
    temperature: float = 0.7
    max_retries: int = 3

    @property
    def api_key(self) -> str:
        if self.provider == "siliconflow":
            return self.siliconflow_api_key or os.getenv("SILICONFLOW_API_KEY", "")
        elif self.provider == "nvidia":
            return self.nvidia_api_key or os.getenv("NVIDIA_API_KEY", "")
        return ""


class ExchangeSettings(BaseSettings):
    """交易所配置"""

    id: str = "binance"
    rate_limit: bool = True
    proxy: Optional[str] = None


class AnalysisSettings(BaseSettings):
    """分析配置"""

    symbols: List[str] = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    timeframes: List[str] = ["15m", "1h", "1d"]
    klines_limit: int = 50


class MultiTimeframeSettings(BaseSettings):
    """多周期配置"""

    enabled: bool = True
    timeframes: List[str] = ["15m", "1h", "1d"]
    weights: Dict[str, float] = {"15m": 0.3, "1h": 0.6, "1d": 1.0}
    consensus_threshold: float = 0.7


class NotificationSettings(BaseSettings):
    """通知配置"""

    enabled: bool = True
    windows_sound: bool = True
    system_toast: bool = True


class SignalSystemSettings(BaseSettings):
    """信号系统配置"""

    enabled: bool = True
    min_consensus_score: float = 0.9
    min_win_rate: float = 0.65


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    path: str = "./data.db"


class Settings(BaseSettings):
    """主配置类"""

    environment: str = "development"
    log_level: str = "INFO"

    analysis: AnalysisSettings = Field(default_factory=AnalysisSettings)
    exchange: ExchangeSettings = Field(default_factory=ExchangeSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    multi_timeframe: MultiTimeframeSettings = Field(
        default_factory=MultiTimeframeSettings
    )
    notification: NotificationSettings = Field(default_factory=NotificationSettings)
    signal_system: SignalSystemSettings = Field(default_factory=SignalSystemSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PRICEACTION_",
        extra="ignore",
    )

    @classmethod
    def from_env_file(cls, env_path: str = ".env") -> "Settings":
        from pathlib import Path

        env_file = Path(env_path)
        if not env_file.exists():
            return cls()
        return cls(_env_file=str(env_file))


# 全局Settings实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局Settings实例"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env_file()
    return _settings
