-- Migration 001: Supplier Tables
-- Creates the multi-supplier pricing architecture tables for the kerf redesign.
-- Crawlers write prices offline; the app reads from the cache at runtime.

-- =============================================================================
-- TABLES
-- =============================================================================

-- suppliers: Master supplier list
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    base_url    TEXT NOT NULL,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- supplier_prices: Crawled price data (one row per supplier+product combination)
CREATE TABLE IF NOT EXISTS supplier_prices (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id      TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    product_type     TEXT NOT NULL CHECK (product_type IN ('solid', 'sheet')),
    species_or_name  TEXT NOT NULL,
    thickness        TEXT NOT NULL,
    price            NUMERIC(10, 4) NOT NULL,
    unit             TEXT NOT NULL CHECK (unit IN ('board_foot', 'sheet', 'linear_foot')),
    url              TEXT,
    crawled_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (supplier_id, product_type, species_or_name, thickness)
);

-- crawl_runs: Crawl run log
CREATE TABLE IF NOT EXISTS crawl_runs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id   TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMPTZ,
    product_count INTEGER,
    errors        JSONB
);

-- user_preferences: Per-user settings (one row per authenticated user)
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    enabled_suppliers TEXT[]  NOT NULL DEFAULT '{}',
    default_species   TEXT,
    default_sheet_type TEXT,
    default_units     TEXT    NOT NULL DEFAULT 'in' CHECK (default_units IN ('in', 'mm')),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_supplier_prices_supplier_id
    ON supplier_prices (supplier_id);

CREATE INDEX IF NOT EXISTS idx_supplier_prices_crawled_at
    ON supplier_prices (crawled_at DESC);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_supplier_id
    ON crawl_runs (supplier_id);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_started_at
    ON crawl_runs (started_at DESC);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE suppliers         ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_prices   ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_runs        ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences  ENABLE ROW LEVEL SECURITY;

-- suppliers: authenticated users may read; service_role has full access
CREATE POLICY "suppliers_read_authenticated"
    ON suppliers FOR SELECT
    TO authenticated
    USING (TRUE);

CREATE POLICY "suppliers_all_service_role"
    ON suppliers FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- supplier_prices: authenticated users may read; service_role has full access
CREATE POLICY "supplier_prices_read_authenticated"
    ON supplier_prices FOR SELECT
    TO authenticated
    USING (TRUE);

CREATE POLICY "supplier_prices_all_service_role"
    ON supplier_prices FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- crawl_runs: service_role only (internal operational table)
CREATE POLICY "crawl_runs_all_service_role"
    ON crawl_runs FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- user_preferences: each user reads/writes only their own row; service_role full access
CREATE POLICY "user_preferences_read_own"
    ON user_preferences FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "user_preferences_write_own"
    ON user_preferences FOR ALL
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_preferences_all_service_role"
    ON user_preferences FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- =============================================================================
-- SEED DATA
-- =============================================================================

INSERT INTO suppliers (supplier_id, name, base_url, active)
VALUES
    ('woodworkers_source', 'Woodworkers Source',  'https://www.woodworkerssource.com', TRUE),
    ('knotty_lumber',      'Knotty Lumber',        'https://www.knottylumber.com',       TRUE),
    ('makerstock',         'Makerstock',           'https://www.makerstock.com',          TRUE)
ON CONFLICT (supplier_id) DO NOTHING;
