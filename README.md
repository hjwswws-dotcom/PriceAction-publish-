# PriceAction v2.0.0

## Architecture

```
src/
├── config/         # Pydantic settings
├── data_provider/ # CCXT fetcher, database, market context
├── llm/          # LLM providers (SiliconFlow, etc.)
├── strategy/      # Core strategy modules
├── utils/        # Logger, helpers
└── risk/         # Risk analysis
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run the application
python -m src.main --mode both
```

## Features

- Modular architecture with ABC-based providers
- Multi-timeframe analysis
- AI-powered signal classification
- Risk management
- Real-time notifications
