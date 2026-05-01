"""Filing 再パース共通ロジック."""

from __future__ import annotations

from pathlib import Path

from src.parser.configs import load_edinet_config
from src.parser.edinet import utils as xbrl_utils
from src.parser.edinet.xbrl_parser import BalanceSheetSummary, CashFlowSummary, FinancialSummary

from .writer import insert_statements_and_items


def reparse_one(cur, filing_id: int, zip_path: Path, cfg: dict | None = None) -> dict:
    """指定 filing を再パースして statements/statement_items を再生成する.

    既存 statements を DELETE（CASCADE で statement_items も消える）してから
    最新パーサーで再 INSERT する。コミット/ロールバックは呼び出し元で行う。
    """
    if cfg is None:
        cfg = load_edinet_config()

    facts = xbrl_utils.collect_facts_from_zip(zip_path)
    df = xbrl_utils.facts_to_dataframe(facts)
    df = xbrl_utils.add_local_name_column(df)

    fs = FinancialSummary.from_dataframe(df)
    cf = CashFlowSummary.from_dataframe(df)
    bs = BalanceSheetSummary.from_dataframe(df)

    cur.execute("DELETE FROM statements WHERE filing_id = %s", (filing_id,))
    insert_statements_and_items(cur, filing_id, cfg, fs, cf, bs)
    return fs.to_dict()
