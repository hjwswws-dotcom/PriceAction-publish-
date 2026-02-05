-- PriceAction Database Schema
-- Main tables for trading analysis system

-- States table: stores AI analysis states for trading pairs
CREATE TABLE IF NOT EXISTS states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '15m',
    marketCycle TEXT DEFAULT 'TRADING_RANGE',
    activeNarrative TEXT,
    alternativeNarrative TEXT,
    analysis_text TEXT,
    last_updated INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
    UNIQUE(symbol, timeframe)
);

-- Trading signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT UNIQUE,
    symbol TEXT,
    timeframe TEXT,
    signal_level TEXT,
    signal_type TEXT,
    pattern_name TEXT,
    probability TEXT,
    risk_reward REAL,
    entry_trigger REAL,
    stop_loss REAL,
    take_profit REAL,
    timestamp INTEGER,
    status TEXT DEFAULT 'ACTIVE',
    signal_checks TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Warning events table
CREATE TABLE IF NOT EXISTS warning_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    warning_type TEXT,
    message TEXT,
    severity TEXT DEFAULT 'WARNING',
    timestamp INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Multi-timeframe states table
CREATE TABLE IF NOT EXISTS multi_timeframe_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    state_data TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
    UNIQUE(symbol, timeframe)
);

-- Timeframe consensus table
CREATE TABLE IF NOT EXISTS timeframe_consensus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    consensus_score REAL,
    dominant_cycle TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Pattern statistics table
CREATE TABLE IF NOT EXISTS pattern_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    pattern_name TEXT,
    occurrence_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    avg_risk_reward REAL DEFAULT 0,
    last_occurrence INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Trades table (also used for risk analysis records)
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    timeframe TEXT,
    direction TEXT,
    status TEXT DEFAULT 'PENDING',
    entry_price REAL,
    stop_loss REAL,
    take_profit_1 REAL,
    take_profit_2 REAL,
    win_probability REAL DEFAULT 0.5,
    position_size_actual REAL DEFAULT 0.0,
    user_notes TEXT,
    outcome_feedback TEXT,
    -- Risk analysis fields
    risk_reward_expected REAL,
    position_size_suggested REAL,
    risk_amount_percent REAL,
    volatility_atr REAL,
    volatility_atr_15m REAL,
    volatility_atr_1h REAL,
    volatility_atr_1d REAL,
    sharpe_ratio_estimate REAL,
    kelly_fraction REAL,
    kelly_fraction_adjusted REAL,
    max_drawdown_estimate REAL,
    r_multiple_plan TEXT,
    stop_distance_percent REAL,
    ai_risk_analysis TEXT,
    ai_recommendation TEXT,
    risk_level TEXT,
    analysis_timestamp INTEGER,
    entry_time INTEGER,
    exit_time INTEGER,
    pnl REAL,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
    updated_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- News items table
CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id TEXT UNIQUE,
    title TEXT,
    summary TEXT,
    source TEXT,
    url TEXT,
    timestamp INTEGER,
    sentiment TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- News signals table
CREATE TABLE IF NOT EXISTS news_signals (
    id TEXT PRIMARY KEY,
    signal_id TEXT UNIQUE,
    event_type TEXT,
    assets TEXT,
    market_scope TEXT,
    direction_hint TEXT,
    impact_volatility INTEGER,
    tail_risk INTEGER,
    time_horizon TEXT,
    confidence REAL,
    attention_score REAL,
    credibility_score REAL,
    news_ids TEXT,
    evidence_urls TEXT,
    one_line_thesis TEXT,
    full_analysis TEXT,
    rank_score REAL,
    created_time_utc INTEGER,
    expires_at_utc INTEGER,
    is_active INTEGER DEFAULT 1,
    reviewed INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
    updated_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Event clusters table
CREATE TABLE IF NOT EXISTS event_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id TEXT,
    news_ids TEXT,
    assets TEXT,
    event_type TEXT,
    summary TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Logs table
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT,
    message TEXT,
    timestamp INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_states_symbol ON states(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_news_signals_created ON news_signals(created_time_utc);
