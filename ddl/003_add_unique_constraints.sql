-- Migration: add unique constraints to statements and statement_items
-- Safe to run on existing data: dedup first, then add constraints.

-- 1. Remove orphaned statement_items from duplicate statements
DELETE FROM statement_items
WHERE statement_id IN (
    SELECT id FROM statements
    WHERE id NOT IN (
        SELECT MIN(id) FROM statements GROUP BY filing_id, statement_type
    )
);

-- 2. Remove duplicate statements (keep earliest per filing + type)
DELETE FROM statements
WHERE id NOT IN (
    SELECT MIN(id) FROM statements GROUP BY filing_id, statement_type
);

-- 3. Remove duplicate statement_items (keep earliest per statement + key)
DELETE FROM statement_items
WHERE id NOT IN (
    SELECT MIN(id) FROM statement_items GROUP BY statement_id, item_key
);

-- 4. Add unique constraints
ALTER TABLE statements
    ADD CONSTRAINT uq_statements_filing_type UNIQUE (filing_id, statement_type);

ALTER TABLE statement_items
    ADD CONSTRAINT uq_statement_items_key UNIQUE (statement_id, item_key);
