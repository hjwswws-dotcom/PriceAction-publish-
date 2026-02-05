"""
CCXT data fetcher implementation with proper proxy support
"""

import os
import ccxt
from typing import Any, Dict, Optional
from src.data_provider.base import BaseDataProvider, MarketData


class CCXTFetcher(BaseDataProvider):
    """CCXT-based data fetcher with proxy support"""

    def __init__(self, api_key: str = "", secret: str = "", proxy: str = None):
        self._name = "ccxt"

        # 配置交易所
        exchange_config = {
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        }

        # 设置代理 - 通过环境变量
        if proxy:
            if proxy.startswith("socks5://"):
                # SOCKS5代理: 通过环境变量配置
                os.environ["SOCKS_PROXY"] = proxy
                # 移除代理配置，让CCXT使用环境变量
                exchange_config["proxy"] = None
            else:
                exchange_config["proxy"] = proxy

        self.exchange = ccxt.binance(exchange_config)

    @property
    def name(self) -> str:
        return self._name

    def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 100) -> MarketData:
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
