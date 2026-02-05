"""
Response Parser - AI响应解析器
"""

import json
import re
from typing import Dict, Any, Optional


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
            r"\{[^{}]*" + r"\{[^{}]*\}" * 3 + r"[^{}]*\}",  # 简单嵌套JSON
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_text = match.group(1).strip()
                # 清理markdown代码块
                json_text = re.sub(r"^```\w*\s*", "", json_text, flags=re.MULTILINE)
                json_text = re.sub(r"\s*```\s*$", "", json_text, flags=re.MULTILINE)
                return json_text

        # 尝试直接解析整个响应
        try:
            json.loads(text)
            return text
        except:
            pass

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
                }

            # 使用安全的JSON解析
            data = safe_json_loads(json_text)
            if data is None:
                return {
                    "success": False,
                    "error": "JSON解析失败",
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
                        "activeNarrative": tf_data.get("activeNarrative", {}),
                        "alternativeNarrative": tf_data.get("alternativeNarrative", {}),
                        "actionPlan": tf_data.get("actionPlan", {}),
                    }

            # 添加多周期分析
            if "multi_timeframe_analysis" in data:
                for tf in timeframe_states:
                    timeframe_states[tf]["multi_timeframe_analysis"] = data[
                        "multi_timeframe_analysis"
                    ]

            return {
                "success": True,
                "analysis_text": analysis_text,
                "timeframe_states": timeframe_states,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"解析错误: {e}",
            }
