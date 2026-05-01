"""src/ingest/edinet/writer.py の単体テスト（モック DB カーソル使用）."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.ingest.edinet.writer import (
    ensure_company,
    find_existing_filing_id,
    get_existing_doc_ids,
    insert_filing,
    update_filing_meta,
)


def _mock_cur(fetchone_return=None, fetchall_return=None):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_return
    cur.fetchall.return_value = fetchall_return or []
    return cur


class TestEnsureCompany:
    def test_returns_company_id(self) -> None:
        cur = _mock_cur(fetchone_return=(42,))
        result = ensure_company(cur, "E12345", "テスト株式会社", "1234")
        assert result == 42
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "ON CONFLICT" in sql

    def test_normalizes_empty_security_code_to_none(self) -> None:
        cur = _mock_cur(fetchone_return=(1,))
        ensure_company(cur, "E99999", "会社名", "")
        params = cur.execute.call_args[0][1]
        assert params[1] is None  # ticker は None になる


class TestGetExistingDocIds:
    def test_returns_set_of_doc_ids(self) -> None:
        cur = _mock_cur(fetchall_return=[("S100AAA",), ("S100BBB",)])
        result = get_existing_doc_ids(cur)
        assert result == {"S100AAA", "S100BBB"}

    def test_returns_empty_set_when_no_filings(self) -> None:
        cur = _mock_cur(fetchall_return=[])
        assert get_existing_doc_ids(cur) == set()


class TestFindExistingFilingId:
    def test_returns_id_when_found(self) -> None:
        cur = _mock_cur(fetchone_return=(99,))
        assert find_existing_filing_id(cur, 1, "S100XXXX") == 99

    def test_returns_none_when_not_found(self) -> None:
        cur = _mock_cur(fetchone_return=None)
        assert find_existing_filing_id(cur, 1, "S100XXXX") is None


class TestInsertFiling:
    def test_returns_new_filing_id(self) -> None:
        cur = _mock_cur(fetchone_return=(77,))
        meta = {
            "period_start": "2023-04-01",
            "period_end": "2024-03-31",
            "source_zip_path": "/data/S100XXXX.zip",
        }
        result = insert_filing(cur, 1, "S100XXXX", meta, 2024, "FY", "yuho")
        assert result == 77
        params = cur.execute.call_args[0][1]
        assert params[0] == 1  # company_id
        assert params[1] == "S100XXXX"  # edinet_doc_id
        assert params[4] == 2024  # fiscal_year
        assert params[5] == "FY"  # fiscal_period


class TestUpdateFilingMeta:
    def test_calls_update_with_correct_filing_id(self) -> None:
        cur = MagicMock()
        meta = {"period_start": "2023-04-01", "period_end": "2024-03-31", "source_zip_path": "/x"}
        update_filing_meta(cur, 55, meta, 2024, "FY")
        cur.execute.assert_called_once()
        params = cur.execute.call_args[0][1]
        assert params[-1] == 55  # filing_id は最後
