"""
Research Assistant - Provides market data and analyst context
"""

from typing import Dict, Any, Optional
from src.data_provider.ccxt_fetcher import CCXTFetcher
from src.config.settings import get_settings


class ResearchAssistant:
    """Research assistant for market analysis"""

    def __init__(self, config: dict = None):
        """Initialize research assistant"""
        self.settings = get_settings()
        self.fetcher = CCXTFetcher(
            api_key=self.settings.binance_api_key or "",
            secret=self.settings.binance_secret or "",
            proxy=self.settings.proxy_url,
        )

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 50):
        """Fetch OHLCV data"""
        return self.fetcher.fetch_ohlcv(symbol, timeframe, limit)

    def fetch_market_context(self, symbol: str) -> Dict[str, Any]:
        """Fetch market context"""
        return {
            "symbol": symbol,
            "trend": "unknown",
            "volatility": "medium",
        }
