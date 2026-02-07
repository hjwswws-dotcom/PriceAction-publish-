# PriceAction 系统错误文档

> **用途**: 记录系统的已知问题和错误
> **适用范围**: Bug追踪、问题诊断、开发参考
> **最后更新**: 2026-02-07

---

## 一、当前系统状态总览

### 1.1 模块健康度

| 模块 | 状态 | 评分 | 说明 |
|------|------|------|------|
| 图表展示 | ✅ 正常 | 95% | K线时区问题已修复 |
| 主要分析流程 | ⚠️ 警告 | 70% | 能运行，但JSON字段提取不稳定 |
| 快速概览 | ⚠️ 部分 | 60% | 文本切分正常，信号识别损坏 |
| 交易信号系统 | ❌ 损坏 | 20% | AI返回JSON不完整，后处理推断低效 |
| 风险计算器 | ❌ 损坏 | 30% | ResearchAssistant初始化失败 |
| 新闻模块 | ❌ 损坏 | 25% | 前后端数据断裂 |
| **整体评估** | **⚠️ 危险** | **40%** | **建议全面重做** |

---

## 二、详细问题记录

### 2.1 交易信号识别损坏

#### 问题描述
交易信号面板无法正确显示盈亏比、进出场位置、止损止盈等关键信息。

#### 根因分析

**AI返回JSON过于简化**:
```
当前AI返回:
{
  "1d": {"marketCycle": "...", "activeNarrative": {"pattern_name": "...", "probability_value": 0.x}},
  ...
}

期望AI返回:
{
  "1d": {
    "marketCycle": "...",
    "marketStructure": "...",
    "signalConfidence": 80,
    "activeNarrative": {
      "pattern_name": "...",
      "status": "...",
      "key_levels": {"entry_trigger": 0.0, "invalidation_level": 0.0, "profit_target_1": 0.0}
    },
    "actionPlan": {
      "state": "...",
      "direction": "...",
      "entryPrice": 0.0,
      "stopLoss": 0.0,
      "targetPrice": 0.0
    }
  },
  ...
}
```

**影响范围**:
- `src/core/response_parser.py`: 解析结果缺少关键字段
- `frontend/views/signals.py`: 无法显示盈亏比、止损止盈
- `frontend/views/quick_overview.py`: 行动手册缺少具体操作建议

**尝试修复**:
1. ✅ 优化Prompt，提供完整的JSON示例
2. ✅ 添加 `_infer_missing_fields_from_text()` 从文本推断缺失字段
3. ⚠️ 修复效果有限，AI配合度不可控

**当前状态**: ❌ 未完全修复，推断逻辑不可靠

---

### 2.2 新闻模块损坏

#### 问题描述
后端捕捉到新闻但前端无法显示。

#### 问题现象
```
后端输出:
[News] 抓取了 10 条新闻
[News] 提纯了 0 条文档
[News] 提取了 0 个信号

前端显示:
暂无新闻信号
```

#### 根因分析

**流水线状态断裂**:
```
正常流程:
抓取 (news_items) → 提纯 (refined_docs) → 分析 (news_signals)
    status=NEW       status=PENDING        status=COMPLETED

实际流程:
抓取 → 提纯 [❌ 未更新状态] → 分析 [❌ 检查错误表]
```

**具体问题**:
1. `refiner.py` 保存 `refined_docs` 后没有更新 `news_items.status`
2. 步骤3检查 `doc.get("status") == "COMPLETED"`，但 `get_recent_news_items()` 返回的是 `news_items` 表
3. 前端查询逻辑与后端保存逻辑不匹配

**尝试修复**:
1. ✅ 添加 `update_news_item_status()` 方法
2. ✅ 添加 `get_refined_docs_for_analysis()` 方法
3. ✅ 修改 `run_news_pipeline()` 修复状态流程
4. ⚠️ 前端改版为直接显示新闻

**当前状态**: ❌ 未完全修复，前端已改版为显示原始新闻

---

### 2.3 风险计算器损坏

#### 问题描述
风险计算器报错：`'NoneType' object has no attribute 'fetcher'`

#### 错误日志
```
AttributeError: 'NoneType' object has no attribute 'fetcher'

File "E:\PriceAction\frontend\views\risk_calculator.py", line 258, in show
    klines_15m = ra.fetcher.fetch_ohlcv(symbol, "15m", limit=50)
```

#### 根因分析

**ResearchAssistant 初始化失败**:
```python
# risk_calculator.py
ra = get_research_assistant()  # 可能返回 None

# 当配置文件加载失败时
if config:
    return ResearchAssistant(config)
return None  # 返回 None

# 后续代码没有检查
klines_15m = ra.fetcher.fetch_ohlcv(...)  # ❌ AttributeError
```

**降级逻辑复杂**:
- 需要同时处理 ResearchAssistant 为 None 和 fetcher 为 None 两种情况
- CCXT 直接调用缺少代理配置
- 异常处理链路长

**尝试修复**:
1. ✅ 添加 None 检查
2. ✅ 添加 CCXT 降级调用
3. ⚠️ 降级逻辑复杂，维护困难

**当前状态**: ⚠️ 勉强可用，降级逻辑复杂

---

### 2.4 其他已知问题

#### 2.4.1 快速概览周期文本切分
- **状态**: ✅ 已修复
- **问题**: 所有周期显示相同的总分析文本
- **修复**: 添加 `_extract_timeframe_analysis()` 按关键词过滤

#### 2.4.2 K线图表时区
- **状态**: ✅ 已修复
- **问题**: 图表时间慢8小时
- **修复**: 列名转小写时机修正 + 时区工具函数

#### 2.4.3 数据库Schema版本
- **状态**: ⚠️ 需手动删除 data.db
- **问题**: 每次架构变更需要重置数据库

---

## 三、错误代码位置索引

### 3.1 频繁出错的文件

| 文件 | 行号 | 函数 | 常见错误 |
|------|------|------|----------|
| `frontend/views/risk_calculator.py` | 258 | `show()` | AttributeError: NoneType |
| `src/core/response_parser.py` | 148-156 | `parse_multi_timeframe()` | 缺少关键字段 |
| `src/llm/siliconflow_provider.py` | 1318 | `_build_multi_timeframe_prompt()` | JSON格式不规范 |
| `frontend/views/news_signals.py` | 213 | `main()` | 无数据显示 |

### 3.2 数据库相关

| 表名 | 问题 |
|------|------|
| `states` | JSON字段可能为空 |
| `trading_signals` | 填充逻辑可能未执行 |
| `news_signals` | 前端查询结果为空 |

---

## 四、临时解决方案

### 4.1 快速恢复命令

```bash
# 1. 删除数据库（最常用）
del data.db
del data.db-wal
del data.db-shm

# 2. 清理缓存
rd /s /q "%USERPROFILE%\.streamlit"
rd /s /q "E:\PriceAction\.streamlit"

# 3. 重启服务
python -m src.main --mode both
```

### 4.2 前端调试

```python
# 在风险计算器中添加调试输出
st.write("ResearchAssistant:", ra)
st.write("Fetcher:", ra.fetcher if ra else None)
```

### 4.3 后端日志

```bash
# 启用详细日志
set PRICEACTION_LOG_LEVEL=DEBUG
python -m src.main --mode backend
```

---

## 五、重做建议

⚠️ **当前系统架构存在根本性问题，建议全面重做**。

### 5.1 重做优先级

| 优先级 | 模块 | 建议 |
|--------|------|------|
| P0 | 整体架构 | 简化模块间依赖，减少耦合 |
| P0 | Prompt工程 | 建立完整的Prompt测试，确保AI返回完整JSON |
| P1 | 新闻模块 | 独立为微服务，简化状态管理 |
| P1 | 风险计算器 | 去掉ResearchAssistant依赖，直接使用CCXT |
| P2 | 前端优化 | 统一错误处理，建立降级策略 |

### 5.2 架构改进方向

1. **Prompt约束强化**
   - 建立Prompt测试套件
   - 要求AI必须返回完整JSON，否则重试
   - 添加JSON Schema验证

2. **模块解耦**
   - 新闻模块独立
   - 风险计算器简化
   - 数据库访问统一

3. **错误处理标准化**
   - 建立统一的错误码体系
   - 前端降级策略统一
   - 详细的错误日志

---

## 六、版本信息

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| v2.0.4-BreakBackPack | 2026-02-07 | ⚠️ 危险 | 当前版本，存在多个损坏模块 |

---

**文档版本**: 1.0
**最后更新**: 2026-02-07
**维护者**: AI Assistant
