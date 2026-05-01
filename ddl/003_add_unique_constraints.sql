-- Migration: add unique constraints to statements and statement_items
-- Dedup first, then add constraints.
--
-- DELETE ... USING self-join を使用（NOT IN より大幅に高速）。
-- statement_items は statements に ON DELETE CASCADE があるため、
-- 重複 statements を消すと紐づく items も自動削除される。

BEGIN;

-- 1. 重複 statements を削除（同じ filing_id + statement_type のうち id が大きい方を消す）
DELETE FROM statements a
USING statements b
WHERE a.filing_id = b.filing_id
  AND a.statement_type = b.statement_type
  AND a.id > b.id;

-- 2. 同一 statement 内の重複 items を削除（id が大きい方を消す）
DELETE FROM statement_items a
USING statement_items b
WHERE a.statement_id = b.statement_id
  AND a.item_key = b.item_key
  AND a.id > b.id;

-- 3. 一意制約を追加
ALTER TABLE statements
    ADD CONSTRAINT uq_statements_filing_type UNIQUE (filing_id, statement_type);

ALTER TABLE statement_items
    ADD CONSTRAINT uq_statement_items_key UNIQUE (statement_id, item_key);

COMMIT;
