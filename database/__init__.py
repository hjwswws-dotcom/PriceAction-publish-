"""
数据库管理模块
负责SQLite数据库的连接、初始化和CRUD操作
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "./data.db"):
        self.db_path = db_path
        self._init_database()

    def _safe_parse_action_plan(self, data: Dict) -> Optional[Dict]:
        """安全解析actionPlan，兼容旧数据库"""
        try:
            raw = data.get("action_plan_json") or data.get("action_plan")
            return json.loads(raw) if raw else None
        except (TypeError, json.JSONDecodeError):
            return None

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with open("database/schema.sql", "r", encoding="utf-8") as f:
                schema = f.read()

            with self._get_connection() as conn:
                conn.executescript(schema)

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_state(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        获取指定交易对和时间框架的当前状态

        Args:
            symbol: 交易对，如 BTC/USDT
            timeframe: 时间框架，如 15m

        Returns:
            状态字典，如果不存在返回None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM states 
                       WHERE symbol = ? AND timeframe = ?""",
                    (symbol, timeframe),
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                # 🔧 关键修复：立即转换为标准字典
                data = dict(row)

                return {
                    "symbol": data.get("symbol"),
                    "timeframe": data.get("timeframe"),
                    "last_updated": data.get("last_updated"),
                    "marketCycle": data.get("market_cycle"),
                    "activeNarrative": {
                        "pattern_name": data.get("active_pattern"),
                        "status": data.get("pattern_status"),
                        "key_levels": {
                            "entry_trigger": data.get("entry_trigger"),
                            "invalidation_level": data.get("invalidation_level"),
                            "profit_target_1": data.get("profit_target_1"),
                        },
                        "comment": data.get("pattern_comment"),
                        "probability": data.get("probability") or "",
                        "probability_value": data.get("probability_value") or 0.0,
                        "risk_reward": data.get("risk_reward") or 0.0,
                    },
                    "alternativeNarrative": {
                        "pattern_name": data.get("alternative_pattern"),
                        "trigger_condition": data.get("alternative_trigger"),
                    },
                    "raw_response": data.get("raw_response") or "",
                    "analysis_text": data.get("analysis_text") or "",
                    "actionPlan": self._safe_parse_action_plan(data),
                }
        except Exception as e:
            logger.error(f"Failed to get state for {symbol} {timeframe}: {e}")
            return None

    def save_state(self, symbol: str, timeframe: str, state: Dict) -> bool:
        """
        保存或更新状态

        Args:
            symbol: 交易对
            timeframe: 时间框架
            state: 状态字典

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                # 先插入临时记录，成功后更新主记录（原子性）
                conn.execute("BEGIN TRANSACTION")

                # 删除旧记录
                conn.execute(
                    "DELETE FROM states WHERE symbol = ? AND timeframe = ?",
                    (symbol, timeframe),
                )

                # 解析状态结构
                active = state.get("activeNarrative", {})
                active_levels = active.get("key_levels", {})
                alternative = state.get("alternativeNarrative", {})
                action_plan = state.get("actionPlan")

                # 获取新字段（兼容旧数据）
                probability = active.get("probability", "")
                probability_value = active.get("probability_value", 0.0)
                # 自动计算risk_reward（如果没有提供）
                provided_rr = active.get("risk_reward", 0.0)
                if provided_rr and provided_rr > 0:
                    risk_reward = provided_rr
                else:
                    # 从价位计算盈亏比：|target - entry| / |entry - stop|
                    entry = active_levels.get("entry_trigger")
                    stop = active_levels.get("invalidation_level")
                    target = active_levels.get("profit_target_1")
                    if entry and stop and target and entry != stop:
                        risk = abs(entry - stop)
                        reward = abs(target - entry)
                        if risk > 0:
                            risk_reward = round(reward / risk, 2)
                        else:
                            risk_reward = 0.0
                    else:
                        risk_reward = 0.0

                # 序列化action_plan为JSON字符串
                action_plan_json = (
                    json.dumps(action_plan, ensure_ascii=False) if action_plan else None
                )

                # 插入新记录
                conn.execute(
                    """INSERT INTO states (
                        symbol, timeframe, last_updated, market_cycle,
                        active_pattern, pattern_status, entry_trigger,
                        invalidation_level, profit_target_1, pattern_comment,
                        alternative_pattern, alternative_trigger, raw_response,
                        analysis_text, probability, probability_value, risk_reward,
                        action_plan
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        symbol,
                        timeframe,
                        state.get(
                            "last_updated", int(datetime.now().timestamp() * 1000)
                        ),
                        state.get("marketCycle"),
                        active.get("pattern_name"),
                        active.get("status"),
                        active_levels.get("entry_trigger"),
                        active_levels.get("invalidation_level"),
                        active_levels.get("profit_target_1"),
                        active.get("comment"),
                        alternative.get("pattern_name"),
                        alternative.get("trigger_condition"),
                        state.get("raw_response", ""),
                        state.get("analysis_text", ""),
                        probability,
                        probability_value,
                        risk_reward,
                        action_plan_json,
                    ),
                )

                conn.commit()
                logger.info(f"State saved for {symbol} {timeframe}")
                return True

        except Exception as e:
            logger.error(f"Failed to save state for {symbol} {timeframe}: {e}")
            return False

    def log_history(self, symbol: str, timeframe: str, event: Dict) -> bool:
        """
        记录历史事件

        Args:
            symbol: 交易对
            timeframe: 时间框架
            event: 事件字典，包含type, description, price等

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT INTO history (
                        symbol, timeframe, timestamp, event_type, price,
                        previous_status, new_status, description,
                        ai_recommendation, entry_price, stop_loss, target_price,
                        analysis_text, probability, probability_value, risk_reward
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        symbol,
                        timeframe,
                        event.get("timestamp", int(datetime.now().timestamp() * 1000)),
                        event.get("type"),
                        event.get("price"),
                        event.get("previous_status"),
                        event.get("new_status"),
                        event.get("description"),
                        event.get("ai_recommendation"),
                        event.get("entry_price"),
                        event.get("stop_loss"),
                        event.get("target_price"),
                        event.get("analysis_text", ""),
                        event.get("probability", ""),
                        event.get("probability_value", 0.0),
                        event.get("risk_reward", 0.0),
                    ),
                )

            logger.info(f"History logged for {symbol} {timeframe}: {event.get('type')}")
            return True

        except Exception as e:
            logger.error(f"Failed to log history for {symbol} {timeframe}: {e}")
            return False

    def get_history(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """
        获取历史记录

        Args:
            symbol: 交易对
            timeframe: 时间框架
            limit: 返回记录数上限

        Returns:
            历史记录列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM history 
                       WHERE symbol = ? AND timeframe = ?
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (symbol, timeframe, limit),
                )

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get history for {symbol} {timeframe}: {e}")
            return []

    def get_all_states(self) -> List[Dict]:
        """
        获取所有当前状态

        Returns:
            所有状态列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM states ORDER BY symbol, timeframe")
                rows = cursor.fetchall()

                states = []
                for row in rows:
                    # 🔧 关键修复：立即转换为标准字典
                    data = dict(row)

                    states.append(
                        {
                            "symbol": data.get("symbol"),
                            "timeframe": data.get("timeframe"),
                            "last_updated": data.get("last_updated"),
                            "marketCycle": data.get("market_cycle"),
                            "activeNarrative": {
                                "pattern_name": data.get("active_pattern"),
                                "status": data.get("pattern_status"),
                                "key_levels": {
                                    "entry_trigger": data.get("entry_trigger"),
                                    "invalidation_level": data.get(
                                        "invalidation_level"
                                    ),
                                    "profit_target_1": data.get("profit_target_1"),
                                },
                                "comment": data.get("pattern_comment"),
                                "probability": data.get("probability") or "",
                                "probability_value": data.get("probability_value")
                                or 0.0,
                                "risk_reward": data.get("risk_reward") or 0.0,
                                "risk_reward_ratio": data.get("risk_reward") or 0.0,
                            },
                            "alternativeNarrative": {
                                "pattern_name": data.get("alternative_pattern"),
                                "trigger_condition": data.get("alternative_trigger"),
                            },
                            "analysis_text": data.get("analysis_text") or "",
                            "actionPlan": self._safe_parse_action_plan(data),
                        }
                    )

                return states

        except Exception as e:
            logger.error(f"Failed to get all states: {e}")
            return []

    def log_system(
        self, level: str, component: str, message: str, exception: Optional[str] = None
    ) -> bool:
        """
        记录系统日志

        Args:
            level: 日志级别 DEBUG/INFO/WARNING/ERROR
            component: 组件名称
            message: 日志消息
            exception: 异常信息（可选）

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT INTO logs (timestamp, level, component, message, exception)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        int(datetime.now().timestamp() * 1000),
                        level,
                        component,
                        message,
                        exception,
                    ),
                )
            return True
        except Exception as e:
            # 日志记录失败不抛异常，避免循环
            print(f"Failed to log to database: {e}")
            return False

    def get_multi_timeframe_state(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        从multi_timeframe_states表获取状态（多周期专用）

        Args:
            symbol: 交易对
            timeframe: 时间框架

        Returns:
            状态字典，如果不存在返回None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM multi_timeframe_states
                       WHERE symbol = ? AND timeframe = ?""",
                    (symbol, timeframe),
                )
                row = cursor.fetchone()
                if row is None:
                    return None

                # 🔧 关键修复：立即转换为标准字典
                data = dict(row)

                return {
                    "symbol": data.get("symbol"),
                    "timeframe": data.get("timeframe"),
                    "last_updated": data.get("last_updated"),
                    "marketCycle": data.get("market_cycle"),
                    "activeNarrative": {
                        "pattern_name": data.get("active_pattern"),
                        "status": data.get("pattern_status"),
                        "key_levels": {
                            "entry_trigger": data.get("entry_trigger"),
                            "invalidation_level": data.get("invalidation_level"),
                            "profit_target_1": data.get("profit_target_1"),
                        },
                        "comment": data.get("pattern_comment"),
                        "probability": data.get("probability") or "",
                        "probability_value": data.get("probability_value") or 0.0,
                        "risk_reward": data.get("risk_reward") or 0.0,
                    },
                    "alternativeNarrative": {
                        "pattern_name": data.get("alternative_pattern"),
                        "trigger_condition": data.get("alternative_trigger"),
                    },
                    "raw_response": data.get("raw_response") or "",
                    "analysis_text": data.get("analysis_text") or "",
                    "timeframe_weight": data.get("timeframe_weight") or 1.0,
                    "parent_alignment": data.get("parent_alignment") or "NEUTRAL",
                    "actionPlan": self._safe_parse_action_plan(data),
                }
        except Exception as e:
            logger.error(f"Failed to get MTF state for {symbol} {timeframe}: {e}")
            return None

    def save_multi_timeframe_state(
        self, symbol: str, timeframe: str, state: Dict
    ) -> bool:
        """
        保存多周期状态到multi_timeframe_states表

        Args:
            symbol: 交易对
            timeframe: 时间框架
            state: 状态字典

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")

                # 删除旧记录
                conn.execute(
                    "DELETE FROM multi_timeframe_states WHERE symbol = ? AND timeframe = ?",
                    (symbol, timeframe),
                )

                # 提取字段（复用现有逻辑）
                active = state.get("activeNarrative", {})
                active_levels = active.get("key_levels", {})
                alternative = state.get("alternativeNarrative", {})
                action_plan = state.get("actionPlan")

                # 序列化action_plan为JSON字符串
                action_plan_json = (
                    json.dumps(action_plan, ensure_ascii=False) if action_plan else None
                )

                conn.execute(
                    """INSERT INTO multi_timeframe_states (
                        symbol, timeframe, last_updated, market_cycle,
                        active_pattern, pattern_status, entry_trigger,
                        invalidation_level, profit_target_1, pattern_comment,
                        alternative_pattern, alternative_trigger, raw_response,
                        analysis_text, probability, probability_value, risk_reward,
                        timeframe_weight, parent_alignment, action_plan
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        symbol,
                        timeframe,
                        state.get(
                            "last_updated", int(datetime.now().timestamp() * 1000)
                        ),
                        state.get("marketCycle"),
                        active.get("pattern_name"),
                        active.get("status"),
                        active_levels.get("entry_trigger"),
                        active_levels.get("invalidation_level"),
                        active_levels.get("profit_target_1"),
                        active.get("comment"),
                        alternative.get("pattern_name"),
                        alternative.get("trigger_condition"),
                        state.get("raw_response", ""),
                        state.get("analysis_text", ""),
                        active.get("probability", ""),
                        active.get("probability_value", 0.0),
                        active.get("risk_reward", 0.0),
                        state.get("timeframe_weight", 1.0),
                        state.get("parent_alignment", "NEUTRAL"),
                        action_plan_json,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save MTF state: {e}")
            return False

    def get_all_timeframes_for_symbol(self, symbol: str) -> List[Dict]:
        """
        获取某个交易对的所有时间框架状态

        Args:
            symbol: 交易对

        Returns:
            所有时间框架状态列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM multi_timeframe_states
                       WHERE symbol = ? ORDER BY timeframe""",
                    (symbol,),
                )
                rows = cursor.fetchall()

                result = []
                for row in rows:
                    # 🔧 关键修复：立即转换为标准字典
                    data = dict(row)

                    result.append(
                        {
                            "symbol": data.get("symbol"),
                            "timeframe": data.get("timeframe"),
                            "last_updated": data.get("last_updated"),
                            "marketCycle": data.get("market_cycle"),
                            "activeNarrative": {
                                "pattern_name": data.get("active_pattern"),
                                "status": data.get("pattern_status"),
                                "key_levels": {
                                    "entry_trigger": data.get("entry_trigger"),
                                    "invalidation_level": data.get(
                                        "invalidation_level"
                                    ),
                                    "profit_target_1": data.get("profit_target_1"),
                                },
                                "comment": data.get("pattern_comment"),
                                "probability": data.get("probability") or "",
                                "probability_value": data.get("probability_value")
                                or 0.0,
                                "risk_reward": data.get("risk_reward") or 0.0,
                            },
                            "alternativeNarrative": {
                                "pattern_name": data.get("alternative_pattern"),
                                "trigger_condition": data.get("alternative_trigger"),
                            },
                            "raw_response": data.get("raw_response") or "",
                            "analysis_text": data.get("analysis_text") or "",
                            "timeframe_weight": data.get("timeframe_weight") or 1.0,
                            "parent_alignment": data.get("parent_alignment")
                            or "NEUTRAL",
                            "actionPlan": self._safe_parse_action_plan(data),
                        }
                    )

                return result
        except Exception as e:
            logger.error(f"Failed to get all timeframes for {symbol}: {e}")
            return []

    def save_consensus(self, symbol: str, consensus: Dict) -> bool:
        """
        保存周期一致性分析结果

        Args:
            symbol: 交易对
            consensus: 一致性分析字典

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT INTO timeframe_consensus (
                        symbol, timestamp, consensus_direction, confidence,
                        aligned_timeframes, conflicting_timeframes, recommendation,
                        bullish_score, bearish_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        symbol,
                        consensus.get(
                            "timestamp", int(datetime.now().timestamp() * 1000)
                        ),
                        consensus.get("direction", "NEUTRAL"),
                        consensus.get("confidence", 0.0),
                        json.dumps(consensus.get("aligned", [])),
                        json.dumps(consensus.get("conflicting", [])),
                        consensus.get("recommendation", ""),
                        consensus.get("bullish_score", 0.0),
                        consensus.get("bearish_score", 0.0),
                    ),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to save consensus: {e}")
            return False

    def get_latest_consensus(self, symbol: str) -> Optional[Dict]:
        """
        获取最新的周期一致性结果

        Args:
            symbol: 交易对

        Returns:
            一致性分析字典，如果不存在返回None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM timeframe_consensus
                       WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1""",
                    (symbol,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return {
                    "symbol": row["symbol"],
                    "timestamp": row["timestamp"],
                    "direction": row["consensus_direction"],
                    "confidence": row["confidence"],
                    "aligned": (
                        json.loads(row["aligned_timeframes"])
                        if row["aligned_timeframes"]
                        else []
                    ),
                    "conflicting": (
                        json.loads(row["conflicting_timeframes"])
                        if row["conflicting_timeframes"]
                        else []
                    ),
                    "recommendation": row["recommendation"],
                    "bullish_score": row["bullish_score"],
                    "bearish_score": row["bearish_score"],
                }
        except Exception as e:
            logger.error(f"Failed to get consensus for {symbol}: {e}")
            return None

    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        清理旧日志

        Args:
            days: 保留天数

        Returns:
            删除的记录数
        """
        try:
            cutoff = int((datetime.now().timestamp() - days * 86400) * 1000)

            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
                deleted = cursor.rowcount

                cursor = conn.execute(
                    "DELETE FROM history WHERE timestamp < ?", (cutoff,)
                )
                deleted += cursor.rowcount

            logger.info(f"Cleaned up {deleted} old records")
            return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0

    # ==================== Phase 4: 智能信号系统接口 ====================

    def save_signal(self, signal: Dict) -> int:
        """
        保存交易信号

        Args:
            signal: 信号字典，包含所有信号信息

        Returns:
            插入的信号ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO trading_signals (
                        symbol, timeframe, timestamp, signal_level, signal_type,
                        confidence, pattern_name, pattern_status, pattern_quality,
                        entry_trigger, stop_loss, profit_target_1, profit_target_2,
                        risk_reward_ratio, market_cycle, consensus_score,
                        ai_analysis, raw_response, signal_checks,
                        volume_ratio, volume_significance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        signal.get("symbol"),
                        signal.get("timeframe"),
                        signal.get("timestamp", int(datetime.now().timestamp() * 1000)),
                        signal.get("signal_level"),
                        signal.get("signal_type"),
                        signal.get("confidence", 0),
                        signal.get("pattern_name"),
                        signal.get("pattern_status"),
                        signal.get("pattern_quality", 3),
                        signal.get("entry_trigger"),
                        signal.get("stop_loss"),
                        signal.get("profit_target_1"),
                        signal.get("profit_target_2"),
                        # 优先使用 risk_reward，如果没有则使用 risk_reward_ratio
                        signal.get("risk_reward", signal.get("risk_reward_ratio", 0.0)),
                        signal.get("market_cycle"),
                        signal.get("consensus_score", 0.0),
                        signal.get("ai_analysis", ""),
                        signal.get("raw_response", ""),
                        json.dumps(signal.get("signal_checks", {})),
                        signal.get("volume_ratio", 1.0),
                        signal.get("volume_significance", "normal"),
                    ),
                )
                signal_id = cursor.lastrowid
                if signal_id is None:
                    signal_id = -1
                logger.info(
                    f"Signal saved: ID={signal_id}, {signal.get('symbol')} {signal.get('signal_level')}"
                )
                return signal_id
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")
            return -1

    def get_pending_signals(self, symbol: str = "", timeframe: str = "") -> List[Dict]:
        """
        获取未完结的信号（outcome为NULL的记录）

        Args:
            symbol: 可选，筛选特定交易对
            timeframe: 可选，筛选特定时间框架

        Returns:
            未完结信号列表
        """
        try:
            with self._get_connection() as conn:
                query = """SELECT * FROM trading_signals WHERE outcome IS NULL"""
                params = []

                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                if timeframe:
                    query += " AND timeframe = ?"
                    params.append(timeframe)

                query += " ORDER BY timestamp DESC"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                signals = []
                for row in rows:
                    signal = dict(row)
                    # 解析JSON字段
                    if signal.get("signal_checks"):
                        try:
                            signal["signal_checks"] = json.loads(
                                signal["signal_checks"]
                            )
                        except:
                            signal["signal_checks"] = {}
                    signals.append(signal)

                return signals
        except Exception as e:
            logger.error(f"Failed to get pending signals: {e}")
            return []

    def update_signal_outcome(
        self,
        signal_id: int,
        outcome: str,
        outcome_price: float = 0.0,
        pnl_percent: float = 0.0,
    ) -> bool:
        """
        更新信号结果

        Args:
            signal_id: 信号ID
            outcome: 结果 (WIN/LOSS/EXPIRED)
            outcome_price: 出场价格
            pnl_percent: 盈亏百分比

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE trading_signals 
                       SET outcome = ?, outcome_price = ?, outcome_timestamp = ?, pnl_percent = ?
                       WHERE id = ?""",
                    (
                        outcome,
                        outcome_price,
                        int(datetime.now().timestamp() * 1000),
                        pnl_percent,
                        signal_id,
                    ),
                )
                logger.info(
                    f"Signal outcome updated: ID={signal_id}, outcome={outcome}, PnL={pnl_percent}%"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update signal outcome: {e}")
            return False

    def get_signals_by_pattern(self, pattern_name: str, limit: int = 100) -> List[Dict]:
        """
        获取特定形态的历史信号

        Args:
            pattern_name: 形态名称
            limit: 返回数量限制

        Returns:
            信号列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM trading_signals 
                       WHERE pattern_name = ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?""",
                    (pattern_name, limit),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get signals by pattern: {e}")
            return []

    def get_all_signals(self, limit: int = 100, hours: int = 0) -> List[Dict]:
        """
        获取所有交易信号（用于前端信号面板）

        Args:
            limit: 返回数量限制
            hours: 只返回最近N小时的信号，None表示不限制

        Returns:
            信号列表
        """
        try:
            with self._get_connection() as conn:
                if hours:
                    # 计算时间戳
                    from datetime import datetime, timedelta

                    cutoff = int(
                        (datetime.now() - timedelta(hours=hours)).timestamp() * 1000
                    )
                    cursor = conn.execute(
                        """SELECT * FROM trading_signals 
                           WHERE timestamp > ? 
                           ORDER BY timestamp DESC 
                           LIMIT ?""",
                        (cutoff, limit),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT * FROM trading_signals 
                           ORDER BY timestamp DESC 
                           LIMIT ?""",
                        (limit,),
                    )
                rows = cursor.fetchall()

                signals = []
                for row in rows:
                    signal = dict(row)
                    # 解析JSON字段
                    if signal.get("signal_checks"):
                        try:
                            signal["signal_checks"] = json.loads(
                                signal["signal_checks"]
                            )
                        except:
                            signal["signal_checks"] = {}
                    signals.append(signal)

                return signals
        except Exception as e:
            logger.error(f"Failed to get all signals: {e}")
            return []

    def log_warning_event(self, warning: Dict) -> bool:
        """
        记录警告事件

        Args:
            warning: 警告事件字典

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT INTO warning_events (
                        symbol, timeframe, timestamp, warning_type, priority,
                        description, old_state, new_state, trigger_price,
                        current_price, related_signal_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        warning.get("symbol", ""),
                        warning.get("timeframe", ""),
                        warning.get(
                            "timestamp", int(datetime.now().timestamp() * 1000)
                        ),
                        warning.get("warning_type", ""),
                        warning.get("priority", "medium"),
                        warning.get("description", ""),
                        json.dumps(warning.get("old_state", {})),
                        json.dumps(warning.get("new_state", {})),
                        warning.get("trigger_price", 0.0),
                        warning.get("current_price", 0.0),
                        warning.get("related_signal_id", 0),
                    ),
                )
                logger.info(
                    f"Warning logged: {warning.get('symbol')} {warning.get('warning_type')}"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to log warning event: {e}")
            return False

    def get_recent_warnings(self, symbol: str = "", hours: int = 24) -> List[Dict]:
        """
        获取最近的警告事件

        Args:
            symbol: 可选，筛选特定交易对
            hours: 查询过去多少小时

        Returns:
            警告事件列表
        """
        try:
            cutoff = int((datetime.now().timestamp() - hours * 3600) * 1000)

            with self._get_connection() as conn:
                if symbol:
                    cursor = conn.execute(
                        """SELECT * FROM warning_events 
                           WHERE symbol = ? AND timestamp > ? 
                           ORDER BY timestamp DESC""",
                        (symbol, cutoff),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT * FROM warning_events 
                           WHERE timestamp > ? 
                           ORDER BY timestamp DESC""",
                        (cutoff,),
                    )
                rows = cursor.fetchall()

                warnings = []
                for row in rows:
                    warning = dict(row)
                    # 解析JSON字段
                    for field in ["old_state", "new_state"]:
                        if warning.get(field):
                            try:
                                warning[field] = json.loads(warning[field])
                            except:
                                warning[field] = {}
                    warnings.append(warning)

                return warnings
        except Exception as e:
            logger.error(f"Failed to get recent warnings: {e}")
            return []

    def update_pattern_statistics(self, stats: Dict) -> bool:
        """
        更新形态统计信息

        Args:
            stats: 统计数据字典

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO pattern_statistics (
                        pattern_name, total_signals, wins, losses, pending,
                        win_rate, avg_pnl_percent, avg_risk_reward,
                        by_market_cycle, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        stats.get("pattern_name"),
                        stats.get("total_signals", 0),
                        stats.get("wins", 0),
                        stats.get("losses", 0),
                        stats.get("pending", 0),
                        stats.get("win_rate", 0.0),
                        stats.get("avg_pnl_percent", 0.0),
                        stats.get("avg_risk_reward", 0.0),
                        json.dumps(stats.get("by_market_cycle", {})),
                        int(datetime.now().timestamp() * 1000),
                    ),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update pattern statistics: {e}")
            return False

    def get_pattern_statistics(self, pattern_name: str = "") -> Dict:
        """
        获取形态统计信息

        Args:
            pattern_name: 可选，特定形态名称。为None返回所有形态统计

        Returns:
            统计数据字典或列表
        """
        try:
            with self._get_connection() as conn:
                if pattern_name:
                    cursor = conn.execute(
                        "SELECT * FROM pattern_statistics WHERE pattern_name = ?",
                        (pattern_name,),
                    )
                    row = cursor.fetchone()
                    if row:
                        stats = dict(row)
                        if stats.get("by_market_cycle"):
                            try:
                                stats["by_market_cycle"] = json.loads(
                                    stats["by_market_cycle"]
                                )
                            except:
                                stats["by_market_cycle"] = {}
                        return stats
                    return {}
                else:
                    cursor = conn.execute(
                        "SELECT * FROM pattern_statistics ORDER BY win_rate DESC"
                    )
                    rows = cursor.fetchall()

                    all_stats = []
                    for row in rows:
                        stats = dict(row)
                        if stats.get("by_market_cycle"):
                            try:
                                stats["by_market_cycle"] = json.loads(
                                    stats["by_market_cycle"]
                                )
                            except:
                                stats["by_market_cycle"] = {}
                        all_stats.append(stats)

                    # 返回包装后的字典，保持一致性
                    return {"patterns": all_stats, "count": len(all_stats)}
        except Exception as e:
            logger.error(f"Failed to get pattern statistics: {e}")
            return {}

    # ==================== 交易记录追踪接口 ====================

    def create_trade(self, trade: Dict) -> int:
        """
        创建新的交易记录（建仓）

        Args:
            trade: 交易字典，包含：
                - symbol: 交易对
                - timeframe: 时间框架
                - direction: LONG/SHORT
                - entry_price: 入场价格
                - stop_loss: 止损价格
                - take_profit_1: 第一目标位
                - take_profit_2: 第二目标位（可选）
                - entry_signal_id: 关联的信号ID
                - pattern_name: 形态名称
                - market_cycle: 市场周期
                - ai_recommendation: AI建议文本

        Returns:
            交易记录ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO trades (
                        symbol, timeframe, direction, status,
                        entry_price, entry_timestamp, entry_signal_id,
                        stop_loss, take_profit_1, take_profit_2,
                        pattern_name, market_cycle, ai_recommendation,
                        last_check_timestamp, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        trade.get("symbol"),
                        trade.get("timeframe"),
                        trade.get("direction", "LONG"),
                        "OPEN",
                        trade.get("entry_price"),
                        trade.get(
                            "entry_timestamp", int(datetime.now().timestamp() * 1000)
                        ),
                        trade.get("entry_signal_id"),
                        trade.get("stop_loss"),
                        trade.get("take_profit_1"),
                        trade.get("take_profit_2"),
                        trade.get("pattern_name", ""),
                        trade.get("market_cycle", ""),
                        trade.get("ai_recommendation", ""),
                        int(datetime.now().timestamp() * 1000),
                        trade.get("notes", ""),
                    ),
                )
                trade_id = cursor.lastrowid
                logger.info(
                    f"Trade created: ID={trade_id}, {trade.get('symbol')} "
                    f"Entry={trade.get('entry_price')}, SL={trade.get('stop_loss')}"
                )
                return trade_id if trade_id else -1
        except Exception as e:
            logger.error(f"Failed to create trade: {e}")
            return -1

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        exit_reason: str,
        pnl_absolute: float = 0.0,
        pnl_percent: float = 0.0,
        notes: str = "",
    ) -> bool:
        """
        平仓交易记录

        Args:
            trade_id: 交易ID
            exit_price: 出场价格
            exit_reason: 平仓原因（TP1/TP2/SL/EXPIRED/MANUAL）
            pnl_absolute: 绝对盈亏
            pnl_percent: 百分比盈亏
            notes: 备注

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE trades 
                       SET status = 'CLOSED',
                           exit_price = ?,
                           exit_timestamp = ?,
                           exit_reason = ?,
                           pnl_absolute = ?,
                           pnl_percent = ?,
                           notes = CASE WHEN notes = '' THEN ? ELSE notes || '; ' || ? END,
                           updated_at = ?
                       WHERE id = ?""",
                    (
                        exit_price,
                        int(datetime.now().timestamp() * 1000),
                        exit_reason,
                        pnl_absolute,
                        pnl_percent,
                        notes,
                        notes,
                        int(datetime.now().timestamp() * 1000),
                        trade_id,
                    ),
                )
                logger.info(
                    f"Trade closed: ID={trade_id}, Exit={exit_price}, "
                    f"Reason={exit_reason}, PnL={pnl_percent:.2f}%"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to close trade {trade_id}: {e}")
            return False

    def get_open_trades(self, symbol: str = "") -> List[Dict]:
        """
        获取所有开仓中的交易

        Args:
            symbol: 可选，筛选特定交易对

        Returns:
            开仓交易列表
        """
        try:
            with self._get_connection() as conn:
                if symbol:
                    cursor = conn.execute(
                        """SELECT * FROM trades 
                           WHERE status = 'OPEN' AND symbol = ?
                           ORDER BY entry_timestamp DESC""",
                        (symbol,),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT * FROM trades 
                           WHERE status = 'OPEN'
                           ORDER BY entry_timestamp DESC"""
                    )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get open trades: {e}")
            return []

    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:
        """
        获取指定交易记录

        Args:
            trade_id: 交易ID

        Returns:
            交易字典或None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM trades WHERE id = ?",
                    (trade_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get trade {trade_id}: {e}")
            return None

    def get_all_trades(
        self, limit: int = 100, status: str = "", symbol: str = ""
    ) -> List[Dict]:
        """
        获取交易记录列表

        Args:
            limit: 返回数量限制
            status: 可选，筛选状态（OPEN/CLOSED/EXPIRED）
            symbol: 可选，筛选交易对

        Returns:
            交易列表
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM trades WHERE 1=1"
                params = []

                if status:
                    query += " AND status = ?"
                    params.append(status)
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)

                query += " ORDER BY entry_timestamp DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

    def update_trade_check_time(self, trade_id: int) -> bool:
        """
        更新交易最后检查时间

        Args:
            trade_id: 交易ID

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE trades 
                       SET last_check_timestamp = ?
                       WHERE id = ?""",
                    (int(datetime.now().timestamp() * 1000), trade_id),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update trade check time: {e}")
            return False

    def get_trades_statistics(self) -> Dict:
        """
        获取交易统计信息

        Returns:
            统计数据字典
        """
        try:
            with self._get_connection() as conn:
                # 总交易数
                cursor = conn.execute("SELECT COUNT(*) FROM trades")
                total = cursor.fetchone()[0]

                # 开仓中
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE status = 'OPEN'"
                )
                open_count = cursor.fetchone()[0]

                # 已平仓
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE status = 'CLOSED'"
                )
                closed_count = cursor.fetchone()[0]

                # 盈利交易
                cursor = conn.execute(
                    "SELECT COUNT(*), AVG(pnl_percent) FROM trades WHERE pnl_percent > 0"
                )
                row = cursor.fetchone()
                wins = row[0] if row else 0
                avg_win = row[1] if row and row[1] else 0

                # 亏损交易
                cursor = conn.execute(
                    "SELECT COUNT(*), AVG(pnl_percent) FROM trades WHERE pnl_percent < 0"
                )
                row = cursor.fetchone()
                losses = row[0] if row else 0
                avg_loss = row[1] if row and row[1] else 0

                # 计算胜率
                win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

                return {
                    "total_trades": total,
                    "open_trades": open_count,
                    "closed_trades": closed_count,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": win_rate,
                    "avg_win_percent": avg_win,
                    "avg_loss_percent": avg_loss,
                }
        except Exception as e:
            logger.error(f"Failed to get trades statistics: {e}")
            return {}

    # ==================== Phase 4.5: AI风险顾问系统接口 ====================

    def create_risk_analysis(self, trade_plan: Dict) -> int:
        """
        创建新的风险分析记录（用户输入交易计划）

        Args:
            trade_plan: 交易计划字典，包含：
                - symbol: 交易对
                - timeframe: 时间框架
                - direction: LONG/SHORT
                - entry_price: 入场价格
                - stop_loss: 止损价格
                - take_profit_1: 第一目标位
                - take_profit_2: 第二目标位（可选）
                - win_probability: 用户估计胜率(0-1)
                - position_size_actual: 用户计划仓位(%)
                - user_notes: 用户备注

        Returns:
            风险分析记录ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
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
                analysis_id = cursor.lastrowid
                logger.info(
                    f"Risk analysis created: ID={analysis_id}, {trade_plan.get('symbol')} "
                    f"Entry={trade_plan.get('entry_price')}, SL={trade_plan.get('stop_loss')}"
                )
                return analysis_id if analysis_id else -1
        except Exception as e:
            logger.error(f"Failed to create risk analysis: {e}")
            return -1

    def update_risk_analysis_result(self, analysis_id: int, risk_result: Dict) -> bool:
        """
        更新AI风险分析结果

        Args:
            analysis_id: 风险分析记录ID
            risk_result: 风险分析结果字典，包含：
                - risk_reward_expected: 预期盈亏比
                - position_size_suggested: AI建议仓位(%)
                - risk_amount_percent: 风险金额(%)
                - volatility_atr: ATR波动率
                - volatility_atr_15m: 15分钟ATR
                - volatility_atr_1h: 1小时ATR
                - volatility_atr_1d: 日线ATR
                - sharpe_ratio_estimate: 估计夏普比率
                - kelly_fraction: 凯利公式最优仓位
                - kelly_fraction_adjusted: 保守调整后的凯利仓位
                - max_drawdown_estimate: 估计最大回撤
                - r_multiple_plan: R-multiple计划(JSON)
                - stop_distance_percent: 止损距离(%)
                - ai_risk_analysis: AI完整风险分析文本
                - ai_recommendation: AI建议摘要
                - risk_level: 风险等级(LOW/MEDIUM/HIGH/EXTREME)

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE trades 
                       SET risk_reward_expected = ?,
                           position_size_suggested = ?,
                           risk_amount_percent = ?,
                           volatility_atr = ?,
                           volatility_atr_15m = ?,
                           volatility_atr_1h = ?,
                           volatility_atr_1d = ?,
                           sharpe_ratio_estimate = ?,
                           kelly_fraction = ?,
                           kelly_fraction_adjusted = ?,
                           max_drawdown_estimate = ?,
                           r_multiple_plan = ?,
                           stop_distance_percent = ?,
                           ai_risk_analysis = ?,
                           ai_recommendation = ?,
                           risk_level = ?,
                           analysis_timestamp = ?,
                           updated_at = ?
                       WHERE id = ?""",
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
                logger.info(f"Risk analysis result updated: ID={analysis_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update risk analysis result {analysis_id}: {e}")
            return False

    def get_risk_analysis(self, analysis_id: int) -> Optional[Dict]:
        """
        获取指定风险分析记录

        Args:
            analysis_id: 风险分析记录ID

        Returns:
            风险分析字典或None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM trades WHERE id = ?",
                    (analysis_id,),
                )
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    # 解析JSON字段
                    if result.get("r_multiple_plan"):
                        try:
                            result["r_multiple_plan"] = json.loads(
                                result["r_multiple_plan"]
                            )
                        except:
                            result["r_multiple_plan"] = {}
                    return result
                return None
        except Exception as e:
            logger.error(f"Failed to get risk analysis {analysis_id}: {e}")
            return None

    def get_risk_analysis_history(
        self, symbol: str = "", status: str = "", limit: int = 100
    ) -> List[Dict]:
        """
        获取风险分析历史记录

        Args:
            symbol: 可选，筛选特定交易对
            status: 可选，筛选状态(ANALYZED/CLOSED/EXPIRED)
            limit: 返回数量限制

        Returns:
            风险分析记录列表
        """
        try:
            with self._get_connection() as conn:
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

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    result = dict(row)
                    # 解析JSON字段
                    if result.get("r_multiple_plan"):
                        try:
                            result["r_multiple_plan"] = json.loads(
                                result["r_multiple_plan"]
                            )
                        except:
                            result["r_multiple_plan"] = {}
                    results.append(result)

                return results
        except Exception as e:
            logger.error(f"Failed to get risk analysis history: {e}")
            return []

    def close_risk_analysis(
        self, analysis_id: int, outcome_feedback: str = "", notes: str = ""
    ) -> bool:
        """
        用户标记关闭风险分析记录（记录实际结果反馈）

        Args:
            analysis_id: 风险分析记录ID
            outcome_feedback: 用户反馈的实际结果(WIN/LOSS/其他)
            notes: 备注

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE trades 
                       SET status = 'CLOSED',
                           outcome_feedback = ?,
                           user_notes = CASE WHEN user_notes = '' THEN ? ELSE user_notes || '; ' || ? END,
                           updated_at = ?
                       WHERE id = ?""",
                    (
                        outcome_feedback,
                        notes,
                        notes,
                        int(datetime.now().timestamp() * 1000),
                        analysis_id,
                    ),
                )
                logger.info(
                    f"Risk analysis closed: ID={analysis_id}, outcome={outcome_feedback}"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to close risk analysis {analysis_id}: {e}")
            return False

    def expire_risk_analysis(self, analysis_id: int) -> bool:
        """
        将风险分析记录标记为过期

        Args:
            analysis_id: 风险分析记录ID

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE trades 
                       SET status = 'EXPIRED',
                           updated_at = ?
                       WHERE id = ?""",
                    (
                        int(datetime.now().timestamp() * 1000),
                        analysis_id,
                    ),
                )
                logger.info(f"Risk analysis expired: ID={analysis_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to expire risk analysis {analysis_id}: {e}")
            return False

    # ==================== Phase 6: 新闻情报模块接口 ====================

    def save_news_item(self, item) -> str:
        """
        保存新闻条目

        Args:
            item: NewsItem对象或字典

        Returns:
            保存的条目ID（UUID）
        """
        try:
            # 兼容 NewsItem 对象和字典
            if hasattr(item, "model_dump"):
                # Pydantic 对象转字典
                data = item.model_dump()
            elif hasattr(item, "__dict__"):
                # 普通对象
                data = item.__dict__
            elif isinstance(item, dict):
                data = item
            else:
                logger.error(f"Unknown item type: {type(item)}")
                return ""

            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO news_items (
                        id, source, source_item_id, title, url,
                        published_time_utc, ingest_time_utc,
                        content, language,
                        votes_positive, votes_negative, votes_installed,
                        domain, kind, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data.get("id"),
                        data.get("source"),
                        data.get("source_item_id"),
                        data.get("title"),
                        data.get("url"),
                        data.get("published_time_utc"),
                        data.get("ingest_time_utc"),
                        data.get("content"),
                        data.get("language"),
                        data.get("votes_positive", 0),
                        data.get("votes_negative", 0),
                        data.get("votes_installed", 0),
                        data.get("domain"),
                        data.get("kind"),
                        data.get("status", "NEW"),
                        data.get("created_at"),
                        data.get("updated_at"),
                    ),
                )
                if cursor.rowcount > 0:
                    item_id = data.get("id", "")
                    if item_id:
                        logger.debug(f"News item saved: {item_id[:8]}...")
                    return item_id
                else:
                    # 已存在，返回已有ID
                    cursor = conn.execute(
                        "SELECT id FROM news_items WHERE source = ? AND source_item_id = ?",
                        (data.get("source"), data.get("source_item_id")),
                    )
                    row = cursor.fetchone()
                    return row["id"] if row and row["id"] else data.get("id", "")
        except Exception as e:
            logger.error(f"Failed to save news item: {e}")
            return ""

    def get_news_item(self, news_id: str) -> Optional[Dict]:
        """
        获取新闻条目

        Args:
            news_id: 新闻条目ID

        Returns:
            新闻条目字典或None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM news_items WHERE id = ?",
                    (news_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get news item {news_id}: {e}")
            return None

    def get_pending_news_items(self, limit: int = 100) -> List[Dict]:
        """
        获取待处理的新闻条目

        Args:
            limit: 返回数量限制

        Returns:
            新闻条目列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM news_items
                       WHERE status = 'NEW'
                       ORDER BY published_time_utc DESC
                       LIMIT ?""",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get pending news items: {e}")
            return []

    def get_recent_news_items(self, limit: int = 50) -> List[Dict]:
        """
        获取最近的新闻条目（用于流水线处理）

        Args:
            limit: 返回数量限制

        Returns:
            新闻条目列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM news_items
                       ORDER BY published_time_utc DESC
                       LIMIT ?""",
                    (limit,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get recent news items: {e}")
            return []

    def update_news_status(
        self, news_id: str, status: str, error: Optional[str] = None
    ) -> bool:
        """
        更新新闻条目状态

        Args:
            news_id: 新闻条目ID
            status: 新状态
            error: 错误信息（可选）

        Returns:
            是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE news_items
                       SET status = ?, error = ?, updated_at = ?
                       WHERE id = ?""",
                    (
                        status,
                        error,
                        int(datetime.now().timestamp() * 1000),
                        news_id,
                    ),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update news status: {e}")
            return False

    def save_refined_doc(self, doc) -> str:
        """
        保存提纯文档

        Args:
            doc: RefinedDoc对象或字典

        Returns:
            保存的文档ID（UUID）
        """
        try:
            # 兼容性处理：如果传入的是 Pydantic 对象，转为字典
            if hasattr(doc, "model_dump"):
                data = doc.model_dump()
            elif hasattr(doc, "dict"):
                data = doc.dict()
            elif isinstance(doc, dict):
                data = doc
            else:
                logger.error(f"Unknown doc type: {type(doc)}")
                return ""

            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO refined_docs (
                        id, news_id, final_url, url_hash,
                        content_type, markdown, text_content,
                        extract_method, content_hash, simhash,
                        status, refine_time_utc, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        data.get("id"),
                        data.get("news_id"),
                        data.get("final_url"),
                        data.get("url_hash"),
                        data.get("content_type"),
                        data.get("markdown"),
                        data.get("text_content"),
                        data.get("extract_method"),
                        data.get("content_hash"),
                        data.get("simhash"),
                        data.get("status", "COMPLETED"),
                        data.get("refine_time_utc"),
                        data.get("created_at"),
                    ),
                )
                doc_id = data.get("id", "")
                if doc_id:
                    logger.debug(f"Refined doc saved: {doc_id[:8]}...")
                return doc_id
        except Exception as e:
            logger.error(f"Failed to save refined doc: {e}")
            return ""

    def get_refined_doc_by_news_id(self, news_id: str) -> Optional[Dict]:
        """
        通过news_id获取提纯文档

        Args:
            news_id: 新闻条目ID

        Returns:
            提纯文档字典或None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM refined_docs WHERE news_id = ? ORDER BY created_at DESC LIMIT 1",
                    (news_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get refined doc for {news_id}: {e}")
            return None

    def save_news_signal(self, signal: Dict) -> str:
        """
        保存新闻信号

        Args:
            signal: 新闻信号字典

        Returns:
            保存的信号ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT OR REPLACE INTO news_signals (
                        id, signal_id, event_type, assets, market_scope,
                        direction_hint, impact_volatility, tail_risk,
                        time_horizon, confidence, attention_score, credibility_score,
                        news_ids, evidence_urls,
                        one_line_thesis, full_analysis,
                        rank_score, created_time_utc,
                        expires_at_utc, is_active, reviewed,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        signal.get("id"),
                        signal.get("signal_id"),
                        signal.get("event_type"),
                        json.dumps(signal.get("assets", [])),
                        signal.get("market_scope"),
                        signal.get("direction_hint"),
                        signal.get("impact_volatility", 1),
                        signal.get("tail_risk", 1),
                        signal.get("time_horizon", "hours"),
                        signal.get("confidence", 0.5),
                        signal.get("attention_score", 0.0),
                        signal.get("credibility_score", 0.5),
                        json.dumps(signal.get("news_ids", [])),
                        json.dumps(signal.get("evidence_urls", [])),
                        signal.get("one_line_thesis"),
                        signal.get("full_analysis"),
                        signal.get("rank_score", 0.0),
                        signal.get("created_time_utc"),
                        signal.get("expires_at_utc"),
                        signal.get("is_active", 1),
                        signal.get("reviewed", 0),
                        signal.get("created_at"),
                        signal.get("updated_at"),
                    ),
                )
                signal_id = signal.get("signal_id", "")
                logger.info(f"News signal saved: {signal_id}")
                return signal_id
        except Exception as e:
            logger.error(f"Failed to save news signal: {e}")
            return ""

    def get_latest_news_signals(
        self,
        window_hours: int = 6,
        topk: int = 5,
        min_rank_score: float = 0.3,
        assets: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        获取最新的新闻信号（用于注入AI Prompt）

        Args:
            window_hours: 时间窗口（小时）
            topk: 返回数量上限
            min_rank_score: 最小排序分数
            assets: 筛选特定资产

        Returns:
            新闻信号列表
        """
        try:
            cutoff = int(datetime.now().timestamp() * 1000) - window_hours * 3600 * 1000

            with self._get_connection() as conn:
                if assets:
                    # 构建LIKE查询
                    asset_conditions = " OR ".join([f"assets LIKE ?" for _ in assets])
                    cursor = conn.execute(
                        f"""SELECT * FROM news_signals
                            WHERE created_time_utc > ?
                            AND is_active = 1
                            AND rank_score >= ?
                            AND ({asset_conditions})
                            ORDER BY rank_score DESC
                            LIMIT ?""",
                        [cutoff, min_rank_score]
                        + [f'%"{a}"%' for a in assets]
                        + [topk],
                    )
                else:
                    cursor = conn.execute(
                        """SELECT * FROM news_signals
                           WHERE created_time_utc > ?
                           AND is_active = 1
                           AND rank_score >= ?
                           ORDER BY rank_score DESC
                           LIMIT ?""",
                        (cutoff, min_rank_score, topk),
                    )

                rows = cursor.fetchall()
                signals = []
                for row in rows:
                    signal = dict(row)
                    # 解析JSON字段
                    signal["assets"] = json.loads(signal["assets"])
                    signal["news_ids"] = json.loads(signal["news_ids"])
                    signal["evidence_urls"] = json.loads(signal["evidence_urls"])
                    signals.append(signal)

                return signals
        except Exception as e:
            logger.error(f"Failed to get latest news signals: {e}")
            return []

    def get_news_signals_by_assets(
        self, assets: List[str], limit: int = 50
    ) -> List[Dict]:
        """
        获取特定资产的新闻信号

        Args:
            assets: 资产列表
            limit: 返回数量限制

        Returns:
            新闻信号列表
        """
        try:
            with self._get_connection() as conn:
                conditions = " OR ".join([f"assets LIKE ?" for _ in assets])
                cursor = conn.execute(
                    f"""SELECT * FROM news_signals
                        WHERE ({conditions})
                        ORDER BY created_time_utc DESC
                        LIMIT ?""",
                    [f'%"{a}"%' for a in assets] + [limit],
                )

                rows = cursor.fetchall()
                signals = []
                for row in rows:
                    signal = dict(row)
                    signal["assets"] = json.loads(signal["assets"])
                    signal["news_ids"] = json.loads(signal["news_ids"])
                    signal["evidence_urls"] = json.loads(signal["evidence_urls"])
                    signals.append(signal)

                return signals
        except Exception as e:
            logger.error(f"Failed to get news signals by assets: {e}")
            return []

    def get_high_impact_signals(
        self, impact_threshold: int = 3, tail_risk_threshold: int = 2, limit: int = 20
    ) -> List[Dict]:
        """
        获取高影响信号（用于告警）

        Args:
            impact_threshold: 最小波动影响阈值
            tail_risk_threshold: 最小尾部风险阈值
            limit: 返回数量限制

        Returns:
            高影响信号列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM news_signals
                       WHERE is_active = 1
                       AND (impact_volatility >= ? OR tail_risk >= ?)
                       ORDER BY rank_score DESC
                       LIMIT ?""",
                    (impact_threshold, tail_risk_threshold, limit),
                )

                rows = cursor.fetchall()
                signals = []
                for row in rows:
                    signal = dict(row)
                    signal["assets"] = json.loads(signal["assets"])
                    signal["news_ids"] = json.loads(signal["news_ids"])
                    signal["evidence_urls"] = json.loads(signal["evidence_urls"])
                    signals.append(signal)

                return signals
        except Exception as e:
            logger.error(f"Failed to get high impact signals: {e}")
            return []

    def deactivate_expired_signals(self) -> int:
        """
        标记过期的信号为非活跃

        Returns:
            更新的记录数
        """
        try:
            now = int(datetime.now().timestamp() * 1000)
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """UPDATE news_signals
                       SET is_active = 0, updated_at = ?
                       WHERE expires_at_utc IS NOT NULL
                       AND expires_at_utc < ?
                       AND is_active = 1""",
                    (now, now),
                )
                if cursor.rowcount > 0:
                    logger.info(f"Deactivated {cursor.rowcount} expired signals")
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to deactivate expired signals: {e}")
            return 0

    def cleanup_old_news_data(self, days: int = 30) -> Dict[str, int]:
        """
        清理旧新闻数据

        Args:
            days: 保留天数

        Returns:
            各表删除数量的字典
        """
        try:
            cutoff = int((datetime.now().timestamp() - days * 86400) * 1000)

            deleted = {}

            with self._get_connection() as conn:
                # 清理过期信号
                cursor = conn.execute(
                    "DELETE FROM news_signals WHERE created_time_utc < ?",
                    (cutoff,),
                )
                deleted["signals"] = cursor.rowcount

                # 清理旧聚类
                cursor = conn.execute(
                    "DELETE FROM event_clusters WHERE created_at < ?",
                    (cutoff,),
                )
                deleted["clusters"] = cursor.rowcount

                # 清理7天前的refined_docs
                cutoff_refined = int((datetime.now().timestamp() - 7 * 86400) * 1000)
                cursor = conn.execute(
                    "DELETE FROM refined_docs WHERE created_at < ?",
                    (cutoff_refined,),
                )
                deleted["refined_docs"] = cursor.rowcount

                # 清理7天前的news_items
                cursor = conn.execute(
                    "DELETE FROM news_items WHERE created_at < ?",
                    (cutoff_refined,),
                )
                deleted["news_items"] = cursor.rowcount

            logger.info(f"Cleaned up news data: {deleted}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old news data: {e}")
            return {}
