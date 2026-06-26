-- ZEITGEIST ARBITRAGE ENGINE - Database Schema

-- 1. Raw ingestion staging table
CREATE TABLE IF NOT EXISTS raw_signals (
    id            BIGSERIAL PRIMARY KEY,
    platform      VARCHAR(30)  NOT NULL,
    topic_text    TEXT         NOT NULL,
    engagement    INTEGER      DEFAULT 0,
    region        VARCHAR(50)  NOT NULL,
    source_tier   VARCHAR(20)  CHECK (source_tier IN ('niche', 'mid', 'mainstream')),
    scraped_at    TIMESTAMPTZ  DEFAULT NOW(),
    processed     BOOLEAN      DEFAULT FALSE
);

-- 2. Enriched trend signals (after NLP processing)
CREATE TABLE IF NOT EXISTS trend_signals (
    id            BIGSERIAL PRIMARY KEY,
    topic_slug    VARCHAR(100) NOT NULL,
    platform      VARCHAR(30),
    sentiment     VARCHAR(10),
    velocity      FLOAT        DEFAULT 0.0,
    source_tier   VARCHAR(20),
    engagement    INTEGER      DEFAULT 0,
    region        VARCHAR(50),
    is_nostalgia  BOOLEAN      DEFAULT FALSE,
    signal_at     TIMESTAMPTZ  DEFAULT NOW()
);

-- 3. Market supply data (Uzum, OLX, Alibaba)
CREATE TABLE IF NOT EXISTS market_supply (
    id             BIGSERIAL PRIMARY KEY,
    product_slug   VARCHAR(100) NOT NULL,
    platform       VARCHAR(50),
    listing_count  INTEGER      DEFAULT 0,
    avg_price      NUMERIC(12,2),
    region         VARCHAR(50),
    alibaba_orders INTEGER      DEFAULT 0,
    recorded_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- 4. Scored opportunities (final output)
CREATE TABLE IF NOT EXISTS opportunities (
    id              BIGSERIAL PRIMARY KEY,
    topic_slug      VARCHAR(100) NOT NULL,
    region          VARCHAR(50),
    demand_score    FLOAT        DEFAULT 0.0,
    supply_gap      FLOAT        DEFAULT 0.0,
    cultural_fit    FLOAT        DEFAULT 1.0,
    final_score     FLOAT        DEFAULT 0.0,
    window_weeks    INTEGER      DEFAULT 12,
    entry_strategy  VARCHAR(20),
    marketing_done  BOOLEAN      DEFAULT FALSE,
    detected_at     TIMESTAMPTZ  DEFAULT NOW()
);

-- 5. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_signals_platform   ON raw_signals(platform);
CREATE INDEX IF NOT EXISTS idx_raw_signals_processed  ON raw_signals(processed);
CREATE INDEX IF NOT EXISTS idx_trend_signals_topic    ON trend_signals(topic_slug);
CREATE INDEX IF NOT EXISTS idx_trend_signals_region   ON trend_signals(region);
CREATE INDEX IF NOT EXISTS idx_opportunities_score    ON opportunities(final_score DESC);
