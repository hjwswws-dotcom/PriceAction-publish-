"""
Response Parser - AI响应解析器
"""

import json
import re
from typing import Dict, Any, Optional, List


def safe_json_loads(text: str) -> Optional[Dict]:
    """
    极其健壮的 JSON 解析函数，专门对付 LLM 生成的"脏"数据
    """
    try:
        # 1. 尝试直接解析（非严格模式，允许换行等）
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        try:
            # 2. 如果失败，清理控制字符（换行、制表符等）
            cleaned_text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

            # 3. 提取真正的 JSON 部分（防止 AI 在 JSON 前后加废话）
            json_match = re.search(r"(\{.*\}|\[.*\])", cleaned_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0), strict=False)

            raise
        except Exception as e:
            print(f"❌ 深度解析 JSON 失败: {e}")
            return None


class ResponseParser:
    """AI响应解析器"""

    def parse(self, response_text: str) -> Dict[str, Any]:
        """
        解析双段格式响应

        Args:
            response_text: AI原始响应

        Returns:
            {
                "success": bool,
                "analysis_text": str,  # 详细分析文本
                "state": Dict,         # 状态数据
                "error": str           # 错误信息（如果失败）
            }
        """
        try:
            # 1. 提取JSON部分
            json_text = self._extract_json(response_text)

            if not json_text:
                return {
                    "success": False,
                    "error": "无法找到JSON数据",
                    "analysis_text": response_text,
                }

            # 2. 使用安全的JSON解析
            data = safe_json_loads(json_text)
            if data is None:
                return {
                    "success": False,
                    "error": "JSON解析失败",
                    "analysis_text": response_text,
                }

            # 3. 提取分析文本（JSON之前的所有内容）
            analysis_text = response_text.split("---JSON_DATA_START---")[0].strip()

            return {
                "success": True,
                "analysis_text": analysis_text,
                "state": data,
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析错误: {e}",
                "analysis_text": response_text,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"解析错误: {e}",
                "analysis_text": response_text,
            }

    def _extract_json(self, text: str) -> Optional[str]:
        """从响应文本中提取JSON内容"""
        # 尝试多种模式
        patterns = [
            r"---JSON_DATA_START---\s*(.*?)\s*---JSON_DATA_END---",
            r"```json\s*(.*?)\s*```",  # 匹配markdown代码块
            r"```\s*(\{.*?\})\s*```",  # 匹配无语言标记的代码块
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_text = match.group(1).strip()
                # 清理markdown代码块
                json_text = re.sub(r"^```\w*\s*", "", json_text, flags=re.MULTILINE)
                json_text = re.sub(r"\s*```\s*$", "", json_text, flags=re.MULTILINE)
                return json_text

        # 最后尝试：找最外层的大括号
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            return brace_match.group(0)

        return None

    def parse_multi_timeframe(self, response_text: str) -> Dict[str, Any]:
        """解析多时间框架响应"""
        try:
            # 提取JSON
            json_text = self._extract_json(response_text)

            if not json_text:
                return {
                    "success": False,
                    "error": "无法找到JSON数据",
                    "analysis_text": response_text,
                    "timeframe_states": {},
                }

            # 使用安全的JSON解析
            data = safe_json_loads(json_text)
            if data is None:
                return {
                    "success": False,
                    "error": "JSON解析失败",
                    "analysis_text": response_text,
                    "timeframe_states": {},
                }

            # 提取分析文本
            analysis_text = response_text.split("---JSON_DATA_START---")[0].strip()

            # 构建时间框架状态字典
            timeframe_states = {}

            for tf in ["15m", "1h", "1d"]:
                if tf in data:
                    tf_data = data[tf]
                    timeframe_states[tf] = {
                        "marketCycle": tf_data.get("marketCycle", "TRADING_RANGE"),
                        "marketStructure": tf_data.get("marketStructure", "RANGE"),
                        "signalConfidence": tf_data.get("signalConfidence", 50),
                        "activeNarrative": tf_data.get("activeNarrative", {}),
                        "alternativeNarrative": tf_data.get("alternativeNarrative", {}),
                        "actionPlan": tf_data.get("actionPlan", {}),
                        "volumeProfile": tf_data.get("volumeProfile", {}),
                        "keyLevels": tf_data.get("keyLevels", []),
                    }

            # 添加多周期分析
            if "multi_timeframe_analysis" in data:
                for tf in timeframe_states:
                    timeframe_states[tf]["multi_timeframe_analysis"] = data[
                        "multi_timeframe_analysis"
                    ]

            # 后处理：推断缺失的关键字段（当AI返回的JSON不完整时）
            timeframe_states = self._infer_missing_fields_from_text(analysis_text, timeframe_states)

            return {
                "success": True,
                "analysis_text": analysis_text,
                "timeframe_states": timeframe_states,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"解析错误: {e}",
                "analysis_text": response_text if "response_text" in dir() else "",
                "timeframe_states": {},
            }

    def _infer_missing_fields_from_text(
        self, analysis_text: str, timeframe_states: Dict[str, Dict]
    ) -> Dict[str, Dict]:
        """
        从分析文本中推断缺失的关键字段
        当JSON缺失关键字段时，作为后处理补充

        Args:
            analysis_text: AI原始分析文本
            timeframe_states: 已解析的时间框架状态

        Returns:
            补充后的 timeframe_states
        """
        text_lower = analysis_text.lower()

        for tf, state in timeframe_states.items():
            # 1. 推断 activeNarrative.status
            if "activeNarrative" not in state or not state.get("activeNarrative"):
                state["activeNarrative"] = {}

            active = state["activeNarrative"]

            if not active.get("status"):
                if "信号已触发" in analysis_text or "已突破" in analysis_text:
                    active["status"] = "TRIGGERED"
                elif "形成中" in analysis_text or "构建中" in analysis_text:
                    active["status"] = "FORMING"
                elif "失败" in analysis_text or "失效" in analysis_text:
                    active["status"] = "FAILED"
                elif "完成" in analysis_text:
                    active["status"] = "COMPLETED"
                else:
                    active["status"] = "FORMING"  # 默认

            # 2. 推断 direction（基于趋势关键词）
            if not state.get("actionPlan") or not state.get("actionPlan", {}).get("direction"):
                action_plan = state.get("actionPlan", {})

                if "看涨" in analysis_text or "做多" in analysis_text or "long" in text_lower:
                    direction = "LONG"
                elif "看跌" in analysis_text or "做空" in analysis_text or "short" in text_lower:
                    direction = "SHORT"
                elif "下跌" in analysis_text or "空头" in text_lower:
                    direction = "SHORT"
                elif "上涨" in analysis_text or "多头" in text_lower:
                    direction = "LONG"
                else:
                    direction = "NEUTRAL"

                action_plan["direction"] = direction
                state["actionPlan"] = action_plan

            # 3. 推断 actionPlan.state
            if not state.get("actionPlan") or not state.get("actionPlan", {}).get("state"):
                action_plan = state.get("actionPlan", {})

                if "现价入场" in analysis_text or "立即入场" in analysis_text:
                    action_plan["state"] = "ENTER_NOW"
                elif "挂单" in analysis_text or "等待" in analysis_text:
                    action_plan["state"] = "CONDITIONAL"
                elif "观望" in analysis_text or "等待确认" in analysis_text:
                    action_plan["state"] = "WAIT"
                else:
                    action_plan["state"] = "WAIT"  # 默认

                state["actionPlan"] = action_plan

            # 4. 推断 marketStructure
            if not state.get("marketStructure"):
                if "突破" in analysis_text:
                    state["marketStructure"] = "BOS"
                elif "反转" in analysis_text:
                    state["marketStructure"] = "CHOCH"
                elif "扫损" in analysis_text or "扫" in analysis_text:
                    state["marketStructure"] = "LIQUIDITY_SWEEP"
                else:
                    state["marketStructure"] = "RANGE"

            # 5. 推断 signalConfidence（如果未提供）
            if not state.get("signalConfidence"):
                # 基于概率值估算
                prob = active.get("probability_value", 0)
                if prob >= 0.8:
                    state["signalConfidence"] = 80
                elif prob >= 0.6:
                    state["signalConfidence"] = 60
                elif prob >= 0.4:
                    state["signalConfidence"] = 40
                else:
                    state["signalConfidence"] = 50

            # 6. 推断 key_levels（从文本中提取价格）
            if not active.get("key_levels"):
                key_levels = {}
                prices = self._extract_prices_from_text(analysis_text)
                if prices:
                    # 假设最高价格是阻力/止盈，最低价格是支撑/止损
                    if len(prices) >= 2:
                        key_levels["entry_trigger"] = min(prices)
                        key_levels["invalidation_level"] = (
                            max(prices) + (max(prices) - min(prices)) * 0.02
                        )
                        key_levels["profit_target_1"] = (
                            max(prices) - (max(prices) - min(prices)) * 0.03
                        )
                    elif len(prices) == 1:
                        key_levels["entry_trigger"] = prices[0]
                        key_levels["invalidation_level"] = prices[0] * 1.02
                        key_levels["profit_target_1"] = prices[0] * 0.98

                active["key_levels"] = key_levels

        return timeframe_states

    def _extract_prices_from_text(self, text: str) -> List[float]:
        """
        从文本中提取价格数值

        Args:
            text: 分析文本

        Returns:
            价格数值列表
        """
        # 统一处理：移除所有逗号（中英文）
        text_clean = text.replace(",", "").replace("，", "")

        # 匹配数字（4-8位，可能有小数点）
        matches = re.findall(r"(\d{4,8})", text_clean)

        prices = []
        for match in matches:
            try:
                price = float(match)
                # 加密货币价格通常在 100 - 10,000,000 范围内
                if 100 <= price <= 10000000:
                    prices.append(price)
            except ValueError:
                continue

        return sorted(list(set(prices)))
