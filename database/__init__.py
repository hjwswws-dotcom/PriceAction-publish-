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
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM states ORDER BY symbol")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting states: {e}")
            return []

    def get_state_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get state for a specific symbol"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM states WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting state for {symbol}: {e}")
            return None

    def get_state(self, symbol: str, timeframe: str = "15m") -> Optional[Dict]:
        """Get state for a symbol and timeframe"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM states WHERE symbol = ? AND timeframe = ?", (symbol, timeframe)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting state for {symbol}/{timeframe}: {e}")
            return None

    def get_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trading signals"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM trading_signals ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting signals: {e}")
            return []

    def get_all_signals(self, limit: int = 100, hours: int = 0) -> List[Dict]:
        """Get all trading signals"""
        try:
            self._ensure_connection()
            if hours > 0:
                from datetime import datetime, timedelta

                cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
                cursor = self._conn.execute(
                    """SELECT * FROM trading_signals WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?""",
                    (cutoff, limit),
                )
            else:
                cursor = self._conn.execute(
                    """SELECT * FROM trading_signals ORDER BY timestamp DESC LIMIT ?""", (limit,)
                )
            signals = []
            for row in cursor.fetchall():
                signal = dict(row)
                if signal.get("signal_checks"):
                    try:
                        signal["signal_checks"] = json.loads(signal["signal_checks"])
                    except:
                        signal["signal_checks"] = {}
                signals.append(signal)
            return signals
        except Exception as e:
            print(f"Error getting all signals: {e}")
            return []

    def get_warning_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent warning events"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM warning_events ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting warnings: {e}")
            return []

    def get_news_items(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent news items"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM news_items ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting news: {e}")
            return []

    def get_pattern_statistics(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get pattern statistics"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            if symbol:
                cursor.execute("SELECT * FROM pattern_statistics WHERE symbol = ?", (symbol,))
            else:
                cursor.execute("SELECT * FROM pattern_statistics")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting pattern stats: {e}")
            return []

    def get_multi_timeframe_states(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get multi-timeframe analysis states"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            if symbol:
                cursor.execute("SELECT * FROM multi_timeframe_states WHERE symbol = ?", (symbol,))
            else:
                cursor.execute("SELECT * FROM multi_timeframe_states")
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting multi-timeframe states: {e}")
            return []

    def get_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM trades ORDER BY entry_time DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting trades: {e}")
            return []

    # ==================== Risk Analysis APIs ====================

    def create_risk_analysis(self, trade_plan: Dict) -> int:
        """Create a new risk analysis record"""
        try:
            from datetime import datetime

            self._ensure_connection()
            cursor = self._conn.execute(
                """INSERT INTO trades (
                    symbol, timeframe, direction, status,
                    entry_price, stop_loss, take_profit_1, take_profit_2,
                    win_probability, position_size_actual, user_notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trade_plan.get("symbol"),
                    trade_plan.get("timeframe", "15m"),
                    trade_plan.get("direction", "LONG"),
                    "ANALYZED",
                    trade_plan.get("entry_price"),
                    trade_plan.get("stop_loss"),
                    trade_plan.get("take_profit_1"),
                    trade_plan.get("take_profit_2"),
                    trade_plan.get("win_probability", 0.5),
                    trade_plan.get("position_size_actual", 0.0),
                    trade_plan.get("user_notes", ""),
                    int(datetime.now().timestamp() * 1000),
                    int(datetime.now().timestamp() * 1000),
                ),
            )
            self._conn.commit()
            return cursor.lastrowid if cursor.lastrowid else -1
        except Exception as e:
            print(f"Error creating risk analysis: {e}")
            return -1

    def update_risk_analysis_result(self, analysis_id: int, risk_result: Dict) -> bool:
        """Update AI risk analysis result"""
        try:
            from datetime import datetime

            self._ensure_connection()
            self._conn.execute(
                """UPDATE trades SET risk_reward_expected=?, position_size_suggested=?,
                   risk_amount_percent=?, volatility_atr=?, volatility_atr_15m=?,
                   volatility_atr_1h=?, volatility_atr_1d=?, sharpe_ratio_estimate=?,
                   kelly_fraction=?, kelly_fraction_adjusted=?, max_drawdown_estimate=?,
                   r_multiple_plan=?, stop_distance_percent=?, ai_risk_analysis=?,
                   ai_recommendation=?, risk_level=?, analysis_timestamp=?, updated_at=?
                   WHERE id=?""",
                (
                    risk_result.get("risk_reward_expected", 0.0),
                    risk_result.get("position_size_suggested", 0.0),
                    risk_result.get("risk_amount_percent", 0.0),
                    risk_result.get("volatility_atr", 0.0),
                    risk_result.get("volatility_atr_15m", 0.0),
                    risk_result.get("volatility_atr_1h", 0.0),
                    risk_result.get("volatility_atr_1d", 0.0),
                    risk_result.get("sharpe_ratio_estimate", 0.0),
                    risk_result.get("kelly_fraction", 0.0),
                    risk_result.get("kelly_fraction_adjusted", 0.0),
                    risk_result.get("max_drawdown_estimate", 0.0),
                    json.dumps(risk_result.get("r_multiple_plan", {})),
                    risk_result.get("stop_distance_percent", 0.0),
                    risk_result.get("ai_risk_analysis", ""),
                    risk_result.get("ai_recommendation", ""),
                    risk_result.get("risk_level", "MEDIUM"),
                    int(datetime.now().timestamp() * 1000),
                    int(datetime.now().timestamp() * 1000),
                    analysis_id,
                ),
            )
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error updating risk analysis: {e}")
            return False

    def get_risk_analysis(self, analysis_id: int) -> Optional[Dict]:
        """Get risk analysis by ID"""
        try:
            self._ensure_connection()
            cursor = self._conn.execute("SELECT * FROM trades WHERE id = ?", (analysis_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result.get("r_multiple_plan"):
                    try:
                        result["r_multiple_plan"] = json.loads(result["r_multiple_plan"])
                    except:
                        result["r_multiple_plan"] = {}
                return result
            return None
        except Exception as e:
            print(f"Error getting risk analysis: {e}")
            return None

    def get_risk_analysis_history(
        self, symbol: str = "", status: str = "", limit: int = 100
    ) -> List[Dict]:
        """Get risk analysis history"""
        try:
            self._ensure_connection()
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            cursor = self._conn.execute(query, params)
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result.get("r_multiple_plan"):
                    try:
                        result["r_multiple_plan"] = json.loads(result["r_multiple_plan"])
                    except:
                        result["r_multiple_plan"] = {}
                results.append(result)
            return results
        except Exception as e:
            print(f"Error getting risk analysis history: {e}")
            return []

    def close_risk_analysis(
        self, analysis_id: int, outcome_feedback: str = "", notes: str = ""
    ) -> bool:
        """Close a risk analysis record"""
        try:
            from datetime import datetime

            self._ensure_connection()
            self._conn.execute(
                """UPDATE trades SET status='CLOSED', outcome_feedback=?,
                   user_notes=CASE WHEN user_notes='' THEN ? ELSE user_notes || '; ' || ? END,
                   updated_at=? WHERE id=?""",
                (
                    outcome_feedback,
                    notes,
                    notes,
                    int(datetime.now().timestamp() * 1000),
                    analysis_id,
                ),
            )
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error closing risk analysis: {e}")
            return False

    def expire_risk_analysis(self, analysis_id: int) -> bool:
        """Mark a risk analysis as expired"""
        try:
            from datetime import datetime

            self._ensure_connection()
            self._conn.execute(
                "UPDATE trades SET status='EXPIRED', updated_at=? WHERE id=?",
                (int(datetime.now().timestamp() * 1000), analysis_id),
            )
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error expiring risk analysis: {e}")
            return False

    # ==================== News Signal APIs ====================

    def get_latest_news_signals(self, limit: int = 50) -> List[Dict]:
        """Get latest news signals"""
        try:
            self._ensure_connection()
            cursor = self._conn.execute(
                "SELECT * FROM news_signals ORDER BY created_time_utc DESC LIMIT ?", (limit,)
            )
            signals = []
            for row in cursor.fetchall():
                signal = dict(row)
                signal["assets"] = json.loads(signal["assets"]) if signal.get("assets") else []
                signal["news_ids"] = (
                    json.loads(signal["news_ids"]) if signal.get("news_ids") else []
                )
                signal["evidence_urls"] = (
                    json.loads(signal["evidence_urls"]) if signal.get("evidence_urls") else []
                )
                signals.append(signal)
            return signals
        except Exception as e:
            print(f"Error getting latest news signals: {e}")
            return []

    def get_news_signals_by_assets(self, assets: List[str], limit: int = 50) -> List[Dict]:
        """Get news signals for specific assets"""
        try:
            self._ensure_connection()
            if not assets:
                return []
            conditions = " OR ".join([f"assets LIKE ?" for _ in assets])
            cursor = self._conn.execute(
                f"""SELECT * FROM news_signals WHERE ({conditions}) ORDER BY created_time_utc DESC LIMIT ?""",
                [f'%"{a}"%' for a in assets] + [limit],
            )
            signals = []
            for row in cursor.fetchall():
                signal = dict(row)
                signal["assets"] = json.loads(signal["assets"]) if signal.get("assets") else []
                signal["news_ids"] = (
                    json.loads(signal["news_ids"]) if signal.get("news_ids") else []
                )
                signal["evidence_urls"] = (
                    json.loads(signal["evidence_urls"]) if signal.get("evidence_urls") else []
                )
                signals.append(signal)
            return signals
        except Exception as e:
            print(f"Error getting news signals by assets: {e}")
            return []

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute custom query"""
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
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
