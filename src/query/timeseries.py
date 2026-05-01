"""銘柄の財務時系列データを取得する."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .repositories.company import CompanyRepository
from .repositories.filing import FilingInfo, FilingRepository
from .repositories.statement import StatementRepository


@dataclass
class FinancialTimePoint:
    """時系列上の1点（1決算期分）."""

    fiscal_year: int | None
    fiscal_period: str | None  # 'FY', 'Q1', 'Q2', 'Q3'
    period_end: date | None
    net_sales: float | None
    operating_income: float | None
    ordinary_income: float | None
    net_income: float | None
    eps: float | None


def _build_time_points(
    filings: list[FilingInfo],
    statement_repo: StatementRepository,
) -> list[FinancialTimePoint]:
    """filing 一覧から FinancialTimePoint を一括構築する（バッチクエリ）."""
    summaries = statement_repo.get_financial_summaries_batch([f.id for f in filings])
    return [
        FinancialTimePoint(
            fiscal_year=f.fiscal_year,
            fiscal_period=f.fiscal_period,
            period_end=f.period_end,
            net_sales=summaries[f.id].get("net_sales"),
            operating_income=summaries[f.id].get("operating_income"),
            ordinary_income=summaries[f.id].get("ordinary_income"),
            net_income=summaries[f.id].get("net_income"),
            eps=summaries[f.id].get("eps"),
        )
        for f in filings
    ]


def get_financial_history(
    ticker: str,
    years: int = 5,
    dsn: str | None = None,
) -> list[FinancialTimePoint]:
    """指定銘柄の過去N年分の財務データを取得.

    Args:
        ticker: 証券コード（例: "7203"）
        years: 取得する年数（デフォルト: 5年）
        dsn: PostgreSQL 接続文字列（省略時は環境変数から取得）

    Returns:
        財務時系列データのリスト（period_end 降順）
    """
    company_repo = CompanyRepository(dsn)
    filing_repo = FilingRepository(dsn)
    statement_repo = StatementRepository(dsn)

    company = company_repo.find_by_ticker(ticker)
    if not company:
        return []

    filings = filing_repo.list_annual_filings(company.id, years=years)
    if not filings:
        return []

    return _build_time_points(filings, statement_repo)


def get_financial_history_by_edinet_code(
    edinet_code: str,
    years: int = 5,
    dsn: str | None = None,
) -> list[FinancialTimePoint]:
    """EDINETコードで指定した銘柄の過去N年分の財務データを取得.

    Args:
        edinet_code: EDINETコード
        years: 取得する年数（デフォルト: 5年）
        dsn: PostgreSQL 接続文字列（省略時は環境変数から取得）

    Returns:
        財務時系列データのリスト（period_end 降順）
    """
    company_repo = CompanyRepository(dsn)
    filing_repo = FilingRepository(dsn)
    statement_repo = StatementRepository(dsn)

    company = company_repo.find_by_edinet_code(edinet_code)
    if not company:
        return []

    filings = filing_repo.list_annual_filings(company.id, years=years)
    if not filings:
        return []

    return _build_time_points(filings, statement_repo)


def get_all_periods_history(
    ticker: str,
    years: int = 5,
    fiscal_period: str | None = None,
    dsn: str | None = None,
) -> list[FinancialTimePoint]:
    """指定銘柄の財務データを取得（FY・四半期を含む）.

    Args:
        ticker: 証券コード（例: "7203"）
        years: 取得する年数（デフォルト: 5年）
        fiscal_period: 'FY', 'Q1', 'Q2', 'Q3' で絞り込み。None の場合は全期間
        dsn: PostgreSQL 接続文字列

    Returns:
        財務時系列データのリスト（period_end 降順）
    """
    company_repo = CompanyRepository(dsn)
    filing_repo = FilingRepository(dsn)
    statement_repo = StatementRepository(dsn)

    company = company_repo.find_by_ticker(ticker)
    if not company:
        return []

    filings = filing_repo.list_for_company(company.id, years=years, fiscal_period=fiscal_period)
    if not filings:
        return []

    return _build_time_points(filings, statement_repo)


__all__ = [
    "FinancialTimePoint",
    "get_financial_history",
    "get_financial_history_by_edinet_code",
    "get_all_periods_history",
]
