"""
CCXT data fetcher implementation with proper proxy support
"""

import ccxt
import pandas as pd
from typing import List, Dict


class CCXTFetcher:
    def __init__(self, exchange_id: str = "binance", proxy: str = None, options: Dict = None):
        exchange_config = {"enableRateLimit": True, "options": options or {"defaultType": "swap"}}

        exchange_class = getattr(ccxt, exchange_id, ccxt.binance)
        self.exchange = exchange_class(exchange_config)

        # 统一代理设置逻辑
        if proxy:
            if "socks" in proxy.lower():
                self.exchange.socksProxy = proxy
            else:
                self.exchange.proxies = {"http": proxy, "https": proxy}

    def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 100) -> List[Dict]:
        try:
            # 币安 symbol 格式转换（确保兼容性）
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            result = []
            for candle in ohlcv:
                result.append(
                    {
                        "timestamp": candle[0],
                        "datetime": pd.to_datetime(candle[0], unit="ms").strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                    }
                )
            return result
        except Exception as e:
            print(f"CCXT Error: {e}")
            return []
