# 配置指南

## 快速开始

### 1. 复制配置文件

```bash
# 复制环境变量模板
cp config/.env.example .env

# 复制配置模板（可选，已有config.json时不需要）
cp config/config.example.json config/config.json
```

### 2. 编辑配置文件

#### 编辑 `.env` 文件

```bash
# 使用文本编辑器编辑
notepad .env
# 或
code .env
```

填入你的API密钥：

```env
# SiliconFlow API（国内，推荐）
SILICONFLOW_API_KEY=your_actual_api_key_here

# 代理设置（如果需要）
EXCHANGE_PROXY=socks5://127.0.0.1:10806
```

#### 编辑 `config/config.json` 文件

```json
{
  "llm": {
    "provider": "siliconflow",
    "siliconflow_api_key": "",  // 也可以直接在这里填入API密钥
    "model": "Pro/deepseek-ai/DeepSeek-V3.2"
  },
  "exchange": {
    "proxy": ""  // 或直接在这里填入代理地址
  }
}
```

### 3. 启动系统

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py

# 启动后端
python main.py

# 启动前端（新终端）
streamlit run frontend/app.py
```

---

## 配置说明

### 敏感信息管理

项目支持两种方式管理敏感信息：

#### 方式1：环境变量（推荐）

将敏感信息写入 `.env` 文件：

```env
SILICONFLOW_API_KEY=your_key_here
NVIDIA_API_KEY=your_key_here
EXCHANGE_PROXY=your_proxy_here
DATABASE_PATH=./data.db
CRYPTOPANIC_API_KEY=your_key_here
```

环境变量会覆盖 `config/config.json` 中的对应值。

#### 方式2：直接编辑 config.json

直接将API密钥填入 `config/config.json`：

```json
{
  "llm": {
    "siliconflow_api_key": "your_key_here"
  }
}
```

---

## API 密钥获取

### SiliconFlow（推荐，国内无需代理）

1. 访问 https://cloud.siliconflow.cn/
2. 注册账号并登录
3. 进入「API密钥」页面
4. 创建新的API密钥
5. 复制密钥到 `.env` 或 `config/config.json`

### NVIDIA API（国外，需要代理）

1. 访问 https://developer.nvidia.com/llm-apis
2. 注册NVIDIA开发者账号
3. 申请访问 Llama 或其他模型
4. 获取API密钥
5. 配置代理（`EXCHANGE_PROXY`）

---

## 代理配置

如果无法直接访问交易所或API服务，需要配置代理：

### 常见代理格式

```env
# SOCKS5 代理
EXCHANGE_PROXY=socks5://127.0.0.1:10806

# HTTP 代理
EXCHANGE_PROXY=http://127.0.0.1:7890
```

### VPN 软件端口

| 软件 | SOCKS5 端口 | HTTP 端口 |
|------|------------|-----------|
| v2rayN | 10806 | 10809 |
| Clash | 7891 | 7890 |

---

## 发布公开版

如果要发布公开版仓库，请确保：

1. **删除或清空** `config/config.json` 中的敏感信息
2. **保留** `config/config.example.json` 作为配置模板
3. **保留** `config/.env.example` 作为环境变量模板
4. 确保 `.env` 不会被提交（已在 .gitignore 中配置）
5. 公开版用户只需要：
   ```bash
   cp config/.env.example .env
   # 编辑 .env 填入自己的API密钥
   ```

---

## 故障排除

### Q: 启动后提示缺少API密钥

**解决**：
1. 检查 `.env` 文件是否存在
2. 检查API密钥是否正确填入
3. 检查是否有拼写错误（环境变量名区分大小写）

### Q: 修改配置后不生效

**解决**：
1. 重启后端服务 `python main.py`
2. 清除Python缓存 `rm -rf __pycache__ config/__pycache__`
3. 检查配置路径是否正确

### Q: 代理不工作

**解决**：
1. 确认VPN软件已启动
2. 确认代理端口正确
3. 测试代理连通性：`curl --proxy socks5://127.0.0.1:10806 https://api.siliconflow.cn`
