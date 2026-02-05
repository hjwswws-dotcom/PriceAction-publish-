"""
LLM Provider抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class LLMProvider(ABC):
    """LLM Provider抽象基类，支持多供应商切换"""

    @abstractmethod
    def analyze(
        self, symbol: str, klines: List[Dict], current_state: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        发送价格行为分析请求

        Args:
            symbol: 交易对
            klines: OHLCV数据列表
            current_state: 当前状态(可能为None)

        Returns:
            {
                "success": bool,
                "analysis_text": str,  # 分析文本
                "state": Dict,  # 新状态
                "raw_response": str,  # AI原始回复
                "error": str  # 如果失败
            }
        """
        pass

    @abstractmethod
    def validate_response(self, response: str) -> bool:
        """验证AI响应格式是否正确"""
        pass

    @abstractmethod
    def analyze_multi_timeframe(
        self,
        symbol: str,
        timeframe_data: Dict[str, List[Dict]],
        current_states: Dict[str, Optional[Dict]],
    ) -> Dict[str, Any]:
        """
        执行多时间框架价格行为分析

        Args:
            symbol: 交易对
            timeframe_data: 各时间框架的K线数据
            current_states: 各时间框架的当前状态

        Returns:
            分析结果字典
        """
        pass
