-- Core tables for storing EDINET XBRL financial statements
-- Assumes PostgreSQL

-- 1. companies: 企業マスタ
CREATE TABLE IF NOT EXISTS companies (
    id           BIGSERIAL PRIMARY KEY,
    edinet_code  VARCHAR(20) NOT NULL UNIQUE,
    ticker       VARCHAR(20),
    name_jp      TEXT        NOT NULL,
    name_en      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_ticker
    ON companies (ticker);


-- 2. filings: 提出書類（有報・四半期報告書など）の単位
CREATE TABLE IF NOT EXISTS filings (
    id             BIGSERIAL PRIMARY KEY,
    company_id     BIGINT      NOT NULL REFERENCES companies (id),
    edinet_doc_id  VARCHAR(64) NOT NULL,
    period_start   DATE,
    period_end     DATE,
    fiscal_year    INTEGER,
    fiscal_period  VARCHAR(16),   -- e.g. 'FY2024', 'Q1'
    is_consolidated BOOLEAN       NOT NULL DEFAULT TRUE,
    document_type  VARCHAR(32),   -- e.g. 'yuho', 'shihanki'
    submitted_at   TIMESTAMPTZ,
    source_zip_path TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_filings_company_doc UNIQUE (company_id, edinet_doc_id)
);

CREATE INDEX IF NOT EXISTS idx_filings_company_id
    ON filings (company_id);

CREATE INDEX IF NOT EXISTS idx_filings_company_period_end
    ON filings (company_id, period_end);


-- 3. statements: BS / PL / CF などのステートメント単位
CREATE TABLE IF NOT EXISTS statements (
    id              BIGSERIAL PRIMARY KEY,
    filing_id       BIGINT      NOT NULL REFERENCES filings (id) ON DELETE CASCADE,
    statement_type  VARCHAR(16) NOT NULL,   -- 'BS' | 'PL' | 'CF' など
    currency        VARCHAR(8),             -- e.g. 'JPY'
    unit            VARCHAR(32),            -- e.g. 'thousand_yen'
    role_uri        TEXT,                   -- XBRL role URI (必要なら)
    statement_label TEXT,                   -- 人間向けラベル
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_statements_type
        CHECK (statement_type IN ('BS', 'PL', 'CF'))
);

CREATE INDEX IF NOT EXISTS idx_statements_filing_type
    ON statements (filing_id, statement_type);


-- 4. statement_items: ステートメント内の明細行（BS/PL/CFを1テーブルに集約）
-- ノートブックで作っている df(section, key, label_ja, value) を
-- filing / statement を紐づけた上でここにINSERTする想定。
CREATE TABLE IF NOT EXISTS statement_items (
    id               BIGSERIAL PRIMARY KEY,
    statement_id     BIGINT       NOT NULL REFERENCES statements (id) ON DELETE CASCADE,
    item_key         VARCHAR(128) NOT NULL,  -- FinancialSummary.to_dict() などのキー
    label_ja         TEXT,
    label_en         TEXT,
    taxonomy_element VARCHAR(256),           -- XBRL 要素名 (namespace + local name 等)
    order_index      INTEGER,                -- 表示順
    value_numeric    NUMERIC,               -- 金額など数値（単位は statements.unit 参照）
    value_text       TEXT,                  -- 注記事項など文字列の場合
    context_ref      VARCHAR(128),          -- XBRL contextRef
    unit_ref         VARCHAR(128),          -- XBRL unitRef
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_statement_items_statement_id
    ON statement_items (statement_id);

CREATE INDEX IF NOT EXISTS idx_statement_items_statement_key
    ON statement_items (statement_id, item_key);


-- Optional: convenience views for each statement type
CREATE OR REPLACE VIEW bs_items AS
SELECT
    si.*,
    s.statement_type,
    s.currency,
    s.unit,
    s.filing_id
FROM statement_items si
JOIN statements s ON s.id = si.statement_id
WHERE s.statement_type = 'BS';

CREATE OR REPLACE VIEW pl_items AS
SELECT
    si.*,
    s.statement_type,
    s.currency,
    s.unit,
    s.filing_id
FROM statement_items si
JOIN statements s ON s.id = si.statement_id
WHERE s.statement_type = 'PL';

CREATE OR REPLACE VIEW cf_items AS
SELECT
    si.*,
    s.statement_type,
    s.currency,
    s.unit,
    s.filing_id
FROM statement_items si
JOIN statements s ON s.id = si.statement_id
WHERE s.statement_type = 'CF';


