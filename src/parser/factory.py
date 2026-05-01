"""パーサーの軽量ファクトリー."""

from __future__ import annotations

from src.parser._base import SummaryParser
from src.parser.edinet.xbrl_parser import (
    BalanceSheetSummary,
    CashFlowSummary,
    FinancialSummary,
)

_parsers: dict[str, dict[str, type[SummaryParser]]] = {
    "edinet": {
        "financial": FinancialSummary,
        "cash_flow": CashFlowSummary,
        "balance_sheet": BalanceSheetSummary,
    },
    # "tdnet": {...},  # 将来追加
}


def get_parser(source: str, summary_type: str = "financial") -> type[SummaryParser]:
    """データソース名とサマリータイプから SummaryParser クラスを取得.

    Args:
        source: データソース名 ("edinet", "tdnet" など)
        summary_type: サマリータイプ ("financial", "cash_flow", "balance_sheet")

    Returns:
        対応するサマリークラス（SummaryParser プロトコルを満たす）

    Raises:
        KeyError: 未対応のデータソースまたはサマリータイプの場合

    Example:
        >>> FinancialSummary = get_parser("edinet", "financial")
        >>> summary = FinancialSummary.parse_zip("/path/to/file.zip")
    """
    if source not in _parsers:
        available = ", ".join(_parsers.keys())
        raise KeyError(f"Unknown source: {source}. Available: {available}")

    source_parsers = _parsers[source]
    if summary_type not in source_parsers:
        available = ", ".join(source_parsers.keys())
        raise KeyError(f"Unknown summary_type: {summary_type}. Available: {available}")

    return source_parsers[summary_type]


def list_sources() -> list[str]:
    """利用可能なデータソース一覧を返す."""
    return list(_parsers.keys())


def list_summary_types(source: str) -> list[str]:
    """指定データソースで利用可能なサマリータイプ一覧を返す."""
    if source not in _parsers:
        return []
    return list(_parsers[source].keys())
