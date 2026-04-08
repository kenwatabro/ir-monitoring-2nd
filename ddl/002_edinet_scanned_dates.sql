-- EDINET API のスキャン済み日付を管理するテーブル
-- ある日付のメタデータ取得（documents.json）が完了したことを記録する。
-- これにより再実行時に同じ日付のAPIを叩き直すことを避けられる。

CREATE TABLE IF NOT EXISTS edinet_scanned_dates (
    scan_date      DATE        NOT NULL PRIMARY KEY,
    doc_count      INTEGER     NOT NULL DEFAULT 0,   -- その日の対象書類数
    scanned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE edinet_scanned_dates IS
    'EDINET documents.json を取得した日付の記録。再実行時のAPIスキャンスキップに使用。';
