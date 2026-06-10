CREATE TABLE IF NOT EXISTS crawl_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    note TEXT
);

CREATE TABLE IF NOT EXISTS raw_products (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES crawl_runs(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    source_product_id TEXT,
    sku TEXT,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    segment TEXT,
    current_price NUMERIC,
    original_price NUMERIC,
    stock NUMERIC,
    available BOOLEAN,
    url TEXT,
    image_url TEXT,
    image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    collection_handle TEXT,
    model_key TEXT,
    crawled_at TIMESTAMPTZ NOT NULL,
    crawl_date DATE NOT NULL,
    raw_file TEXT,
    extra_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE raw_products
ADD COLUMN IF NOT EXISTS image_url TEXT;

ALTER TABLE raw_products
ADD COLUMN IF NOT EXISTS image_urls JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_products_snapshot
ON raw_products (
    source,
    brand,
    COALESCE(source_product_id, ''),
    COALESCE(sku, ''),
    COALESCE(url, ''),
    crawled_at
);

CREATE INDEX IF NOT EXISTS ix_raw_products_model_date
ON raw_products (model_key, crawl_date);

CREATE INDEX IF NOT EXISTS ix_raw_products_brand_source_date
ON raw_products (brand, source, crawl_date);

CREATE TABLE IF NOT EXISTS daily_price_comparisons (
    id BIGSERIAL PRIMARY KEY,
    comparison_date DATE NOT NULL,
    model_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    gia_ban_phongvu NUMERIC,
    gia_goc_phongvu NUMERIC,
    url_phongvu TEXT,
    gia_ban_gearvn NUMERIC,
    gia_goc_gearvn NUMERIC,
    url_gearvn TEXT,
    gia_ban_cellphones NUMERIC,
    gia_goc_cellphones NUMERIC,
    url_cellphones TEXT,
    image_url TEXT,
    so_website_co_hang INTEGER NOT NULL DEFAULT 0,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (comparison_date, model_key, brand)
);

ALTER TABLE daily_price_comparisons
ADD COLUMN IF NOT EXISTS image_url TEXT;

CREATE INDEX IF NOT EXISTS ix_daily_comparisons_brand_date
ON daily_price_comparisons (brand, comparison_date);

CREATE INDEX IF NOT EXISTS ix_daily_comparisons_model_date
ON daily_price_comparisons (model_key, comparison_date);

CREATE TABLE IF NOT EXISTS app_users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS favorite_products (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    model_key TEXT NOT NULL,
    brand TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, model_key, brand)
);

CREATE INDEX IF NOT EXISTS ix_favorite_products_user
ON favorite_products (user_id, created_at DESC);
