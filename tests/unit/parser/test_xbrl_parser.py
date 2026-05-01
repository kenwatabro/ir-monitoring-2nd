"""xbrl_parser の回帰テスト（実 ZIP ファイルを使用）."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.parser.edinet.xbrl_parser import FinancialSummary

SANRIO_ZIP = Path("data/raw/edinet/S100W57J.zip")


@pytest.mark.skipif(not SANRIO_ZIP.exists(), reason="S100W57J.zip not available")
class TestSanrioFY2025:
    """サンリオ FY2025（S100W57J）の連結通期値回帰テスト."""

    def setup_method(self) -> None:
        self.summary = FinancialSummary.parse_zip(SANRIO_ZIP)

    def test_net_sales(self) -> None:
        assert self.summary.net_sales == 144904000000.0

    def test_operating_income(self) -> None:
        assert self.summary.operating_income == 51806000000.0

    def test_ordinary_income(self) -> None:
        assert self.summary.ordinary_income == 53453000000.0

    def test_net_income_is_consolidated_not_standalone(self) -> None:
        # 単体値 25643000000 ではなく連結値であること
        assert self.summary.net_income == 41731000000.0

    def test_eps(self) -> None:
        assert self.summary.eps == pytest.approx(176.62, rel=1e-4)
