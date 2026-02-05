"""
Database Manager for PriceAction
Simple wrapper for SQLite database access
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class DatabaseManager:
    """Database manager for PriceAction system"""

    def __init__(self, db_path: str = "./data.db"):
        """Initialize database manager"""
        self.db_path = Path(db_path)
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure database connection is valid"""
        if not hasattr(self, "_conn") or self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection"""
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()
            self._conn = None

    def get_all_states(self) -> List[Dict[str, Any]]:
        """Get all trading pair states"""
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM states ORDER BY symbol")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting states: {e}")
            return []

    def get_state_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get state for a specific symbol"""
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM states WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting state for {symbol}: {e}")
            return None

    def get_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trading signals"""
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM trading_signals ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting signals: {e}")
            return []

    def get_warning_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent warning events"""
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM warning_events ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting warnings: {e}")
            return []

    def get_news_items(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent news items"""
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM news_items ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting news: {e}")
            return []

    def get_pattern_statistics(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get pattern statistics"""
        try:
            cursor = self._conn.cursor()
            if symbol:
                cursor.execute("SELECT * FROM pattern_statistics WHERE symbol = ?", (symbol,))
            else:
                cursor.execute("SELECT * FROM pattern_statistics")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting pattern stats: {e}")
            return []

    def get_multi_timeframe_states(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get multi-timeframe analysis states"""
        try:
            cursor = self._conn.cursor()
            if symbol:
                cursor.execute("SELECT * FROM multi_timeframe_states WHERE symbol = ?", (symbol,))
            else:
                cursor.execute("SELECT * FROM multi_timeframe_states")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting multi-timeframe states: {e}")
            return []

    def get_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM trades ORDER BY entry_time DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting trades: {e}")
            return []

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute custom query"""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error executing query: {e}")
            return []

    def __enter__(self):
        """Context manager entry"""
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
