"""
CCXT data fetcher implementation
"""

import ccxt
from typing import Any, Dict
from src.data_provider.base import BaseDataProvider, MarketData


class CCXTFetcher(BaseDataProvider):
    """CCXT-based data fetcher"""

    def __init__(self, api_key: str = "", secret: str = "", proxy: str = None):
        self.name = "ccxt"
        self.exchange = ccxt.binance(
            {
                "apiKey": api_key,
                "secret": secret,
                "enableRateLimit": True,
                "proxy": proxy,
            }
        )

    @property
    def name(self) -> str:
        return "ccxt"

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 100
    ) -> MarketData:
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            ohlcv=ohlcv,
            timestamp=int(__import__("time").time() * 1000),
        )

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return self.exchange.fetch_ticker(symbol)

    def check_health(self) -> bool:
        try:
            self.exchange.fetch_time()
            return True
        except Exception:
            return False
