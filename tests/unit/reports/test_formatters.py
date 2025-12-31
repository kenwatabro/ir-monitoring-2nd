"""Formatter のユニットテスト."""

from __future__ import annotations

from datetime import date

import pytest

from src.query.timeseries import FinancialTimePoint
from src.reports.formatters.console import ConsoleFormatter
from src.reports.formatters.csv import CsvFormatter
from src.reports.formatters.markdown import MarkdownFormatter


@pytest.fixture
def sample_data() -> list[FinancialTimePoint]:
    """テスト用の財務データ."""
    return [
        FinancialTimePoint(
            fiscal_year=2024,
            fiscal_period="FY",
            period_end=date(2024, 3, 31),
            net_sales=30_000_000_000_000,
            operating_income=2_500_000_000_000,
            ordinary_income=2_800_000_000_000,
            net_income=2_000_000_000_000,
            eps=200.50,
        ),
        FinancialTimePoint(
            fiscal_year=2023,
            fiscal_period="FY",
            period_end=date(2023, 3, 31),
            net_sales=28_000_000_000_000,
            operating_income=2_200_000_000_000,
            ordinary_income=2_500_000_000_000,
            net_income=1_800_000_000_000,
            eps=180.00,
        ),
    ]


class TestConsoleFormatter:
    """ConsoleFormatter のテスト."""

    def test_name(self) -> None:
        formatter = ConsoleFormatter()
        assert formatter.name == "console"

    def test_format_empty_data(self) -> None:
        formatter = ConsoleFormatter()
        result = formatter.format([])
        assert result == "データがありません"

    def test_format_with_data(self, sample_data: list[FinancialTimePoint]) -> None:
        formatter = ConsoleFormatter()
        result = formatter.format(sample_data, company_name="テスト会社")

        assert "テスト会社" in result
        assert "財務推移" in result
        assert "売上高" in result
        assert "EPS" in result
        # 百万円単位に変換された値が含まれる
        assert "30,000,000" in result  # 30兆円 = 30,000,000百万円
        assert "200.50" in result  # EPS

    def test_format_sorts_by_fiscal_year(
        self, sample_data: list[FinancialTimePoint]
    ) -> None:
        formatter = ConsoleFormatter()
        result = formatter.format(sample_data)

        # 2023 が 2024 より前に出力される（古い順）
        idx_2023 = result.find("2023")
        idx_2024 = result.find("2024")
        assert idx_2023 < idx_2024


class TestCsvFormatter:
    """CsvFormatter のテスト."""

    def test_name(self) -> None:
        formatter = CsvFormatter()
        assert formatter.name == "csv"

    def test_format_empty_data(self) -> None:
        formatter = CsvFormatter()
        result = formatter.format([])
        assert result == ""

    def test_format_with_data(self, sample_data: list[FinancialTimePoint]) -> None:
        formatter = CsvFormatter()
        result = formatter.format(sample_data)

        lines = result.strip().split("\n")
        assert len(lines) == 3  # ヘッダー + 2行

        # ヘッダー確認
        assert "fiscal_year" in lines[0]
        assert "net_sales" in lines[0]
        assert "eps" in lines[0]

        # データ確認
        assert "2023" in lines[1]  # 古い順
        assert "2024" in lines[2]

    def test_format_handles_none_values(self) -> None:
        formatter = CsvFormatter()
        data = [
            FinancialTimePoint(
                fiscal_year=2024,
                fiscal_period="FY",
                period_end=None,
                net_sales=None,
                operating_income=None,
                ordinary_income=None,
                net_income=None,
                eps=None,
            )
        ]
        result = formatter.format(data)

        lines = result.strip().split("\n")
        assert len(lines) == 2


class TestMarkdownFormatter:
    """MarkdownFormatter のテスト."""

    def test_name(self) -> None:
        formatter = MarkdownFormatter()
        assert formatter.name == "markdown"

    def test_format_empty_data(self) -> None:
        formatter = MarkdownFormatter()
        result = formatter.format([])
        assert result == "データがありません"

    def test_format_with_data(self, sample_data: list[FinancialTimePoint]) -> None:
        formatter = MarkdownFormatter()
        result = formatter.format(sample_data, company_name="テスト会社")

        assert "## テスト会社" in result
        assert "| 決算期 |" in result
        assert "|--------|" in result
        # 百万円単位に変換された値
        assert "30,000,000" in result
        assert "200.50" in result

    def test_format_creates_valid_markdown_table(
        self, sample_data: list[FinancialTimePoint]
    ) -> None:
        formatter = MarkdownFormatter()
        result = formatter.format(sample_data)

        lines = [line for line in result.split("\n") if line.startswith("|")]
        # ヘッダー + セパレータ + 2データ行
        assert len(lines) == 4

        # 各行のパイプ数が一致
        pipe_counts = [line.count("|") for line in lines]
        assert len(set(pipe_counts)) == 1  # 全て同じ



