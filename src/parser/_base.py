"""Parser 基底クラスとプロトコル定義."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import pandas as pd

from src.parser.edinet._base import BaseSummary


@runtime_checkable
class SummaryParser(Protocol):
    """XBRL ZIP から決算サマリーを生成するクラスの構造的インターフェース.

    FinancialSummary / CashFlowSummary / BalanceSheetSummary はこの
    プロトコルを構造的に満たす（明示的継承不要）。
    """

    @classmethod
    def parse_zip(cls, zip_path: Path | str) -> BaseSummary: ...

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> BaseSummary: ...
