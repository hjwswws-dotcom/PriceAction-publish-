"""
Data provider base classes
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MarketData:
    """Market data structure"""

    def __init__(self, symbol: str, timeframe: str, ohlcv: List[Dict], timestamp: int):
        self.symbol = symbol
        self.timeframe = timeframe
        self.ohlcv = ohlcv
        self.timestamp = timestamp


class BaseDataProvider(ABC):
    """Abstract base class for data providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 100
    ) -> MarketData:
        pass

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def check_health(self) -> bool:
        pass
