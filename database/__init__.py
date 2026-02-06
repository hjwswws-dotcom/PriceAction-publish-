"""
Database Manager for PriceAction
Simple wrapper for SQLite database access
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime


def _safe_json_loads(value: Any, default: Any = None) -> Any:
    """安全解析 JSON 字符串

    Args:
        value: 待解析的值（字符串、字典、列表）
        default: 解析失败时的默认值

    Returns:
        解析后的对象或默认值
    """
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


class DatabaseManager:
    """Database manager for PriceAction system"""

    def __init__(self, db_path: str = "./data.db"):
        """Initialize database manager"""
        self.db_path = Path(db_path)
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure database connection is valid (支持多线程)"""
        if not hasattr(self, "_conn") or self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                timeout=30,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            # 启用 WAL 模式，大幅减少读写冲突
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA busy_timeout=30000")
            except Exception as e:
                print(f"[DB] WAL mode setup warning: {e}")

    def _dict_from_item(self, item) -> Dict[str, Any]:
        """Convert Pydantic model or dict to dictionary"""
        if hasattr(item, "model_dump"):
            return item.model_dump()
        return dict(item) if item else {}

    # ==================== News APIs ====================

    def save_news_item(self, item) -> int:
        """Save a news item to the database

        Args:
            item: Pydantic model or dict containing news data

        Returns:
            Inserted news item ID, or -1 on failure
        """
        try:
            data = self._dict_from_item(item)

            self._ensure_connection()
            cursor = self._conn.execute(
                """INSERT OR IGNORE INTO news_items (
                    id, source, source_item_id, title, url,
                    published_time_utc, ingest_time_utc,
                    content, language,
                    votes_positive, votes_negative, votes_installed,
                    domain, kind, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("id", ""),
                    data.get("source", ""),
                    data.get("source_item_id", ""),
                    data.get("title", ""),
                    data.get("url", ""),
                    data.get("published_time_utc", 0),
                    data.get("ingest_time_utc", 0),
                    data.get("content", ""),
                    data.get("language", "en"),
                    data.get("votes_positive", 0),
                    data.get("votes_negative", 0),
                    data.get("votes_installed", 0),
                    data.get("domain", ""),
                    data.get("kind", ""),
                    data.get("status", "NEW"),
                    data.get("created_at", int(datetime.now().timestamp() * 1000)),
                    data.get("updated_at", int(datetime.now().timestamp() * 1000)),
                ),
            )
            self._conn.commit()
            return cursor.lastrowid if cursor.lastrowid else -1
        except Exception as e:
            print(f"Error saving news item: {e}")
            return -1

    def get_recent_news_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent news items

        Args:
            limit: Maximum number of items to return

        Returns:
            List of news item dictionaries
        """
        try:
            self._ensure_connection()
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM news_items ORDER BY published_time_utc DESC LIMIT ?", (limit,)
            )
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item["related_assets"] = _safe_json_loads(item.get("related_assets"), [])
                items.append(item)
            return items
        except Exception as e:
            print(f"Error getting recent news items: {e}")
            return []

    def save_refined_doc(self, doc) -> int:
        """Save a refined document to the database

        Args:
            doc: Pydantic model or dict containing refined document data

        Returns:
            Inserted document ID, or -1 on failure
        """
        try:
            data = self._dict_from_item(doc)

            self._ensure_connection()
            cursor = self._conn.execute(
                """INSERT INTO refined_docs (
                    id, news_id, url, title, markdown_content,
                    summary, key_entities, quotes, status,
                    error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("id", ""),
                    data.get("news_id", ""),
                    data.get("url", ""),
                    data.get("title", ""),
                    data.get("markdown_content", ""),
                    data.get("summary", ""),
                    json.dumps(data.get("key_entities", [])),
                    json.dumps(data.get("quotes", [])),
                    data.get("status", "PENDING"),
                    data.get("error_message", ""),
                    data.get("created_at", int(datetime.now().timestamp() * 1000)),
                    data.get("updated_at", int(datetime.now().timestamp() * 1000)),
                ),
            )
            self._conn.commit()
            return cursor.lastrowid if cursor.lastrowid else -1
        except Exception as e:
            print(f"Error saving refined doc: {e}")
            return -1

    def save_news_signal(self, signal) -> int:
        """Save a news signal to the database

        Args:
            signal: Pydantic model or dict containing news signal data

        Returns:
            Inserted signal ID, or -1 on failure
        """
        try:
            data = self._dict_from_item(signal)

            self._ensure_connection()
            cursor = self._conn.execute(
                """INSERT INTO news_signals (
                    signal_id, event_type, one_line_thesis, assets,
                    direction, confidence, timeframe, impact_volatility,
                    tail_risk, news_ids, evidence_urls, is_active,
                    created_time_utc, expires_time_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("signal_id", ""),
                    data.get("event_type", ""),
                    data.get("one_line_thesis", ""),
                    json.dumps(data.get("assets", [])),
                    data.get("direction", ""),
                    data.get("confidence", 0),
                    data.get("timeframe", "hours"),
                    data.get("impact_volatility", 1),
                    data.get("tail_risk", 1),
                    json.dumps(data.get("news_ids", [])),
                    json.dumps(data.get("evidence_urls", [])),
                    data.get("is_active", 1),
                    data.get("created_time_utc", int(datetime.now().timestamp() * 1000)),
                    data.get("expires_time_utc"),
                ),
            )
            self._conn.commit()
            return cursor.lastrowid if cursor.lastrowid else -1
        except Exception as e:
            print(f"Error saving news signal: {e}")
            return -1

    def get_high_impact_signals(
        self, impact_threshold: float, tail_risk_threshold: float, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get high impact news signals

        Args:
            impact_threshold: Minimum impact volatility threshold
            tail_risk_threshold: Minimum tail risk score threshold
            limit: Maximum number of signals to return

        Returns:
            List of high impact signal dictionaries
        """
        try:
            self._ensure_connection()
            cursor = self._conn.execute(
                """SELECT * FROM news_signals
                   WHERE impact_volatility >= ? AND tail_risk >= ? AND is_active = 1
                   ORDER BY impact_volatility DESC, tail_risk DESC
                   LIMIT ?""",
                (impact_threshold, tail_risk_threshold, limit),
            )
            signals = []
            for row in cursor.fetchall():
                signal = dict(row)
                signal["assets"] = _safe_json_loads(signal.get("assets"), [])
                signal["news_ids"] = _safe_json_loads(signal.get("news_ids"), [])
                signal["evidence_urls"] = _safe_json_loads(signal.get("evidence_urls"), [])
                signals.append(signal)
            return signals
        except Exception as e:
            print(f"Error getting high impact signals: {e}")
            return []

    def deactivate_expired_signals(self) -> int:
        """Deactivate all expired signals

        Returns:
            Number of signals deactivated
        """
        try:
            from datetime import datetime

            self._ensure_connection()
            current_time = int(datetime.now().timestamp() * 1000)

            cursor = self._conn.execute(
                """UPDATE news_signals SET is_active = 0
                   WHERE is_active = 1 AND expires_time_utc IS NOT NULL AND expires_time_utc < ?""",
                (current_time,),
            )
            self._conn.commit()
            deactivated_count = cursor.rowcount

            print(f"Deactivated {deactivated_count} expired signals")
            return deactivated_count
        except Exception as e:
            print(f"Error deactivating expired signals: {e}")
            return 0

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
                signal["signal_checks"] = _safe_json_loads(signal.get("signal_checks"), {})
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
                result["r_multiple_plan"] = _safe_json_loads(result.get("r_multiple_plan"), {})
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
                result["r_multiple_plan"] = _safe_json_loads(result.get("r_multiple_plan"), {})
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
                signal["assets"] = _safe_json_loads(signal.get("assets"), [])
                signal["news_ids"] = _safe_json_loads(signal.get("news_ids"), [])
                signal["evidence_urls"] = _safe_json_loads(signal.get("evidence_urls"), [])
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
                signal["assets"] = _safe_json_loads(signal.get("assets"), [])
                signal["news_ids"] = _safe_json_loads(signal.get("news_ids"), [])
                signal["evidence_urls"] = _safe_json_loads(signal.get("evidence_urls"), [])
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
