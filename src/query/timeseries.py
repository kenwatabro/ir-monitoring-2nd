"""銘柄の財務時系列データを取得する."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .repositories.company import CompanyRepository
from .repositories.filing import FilingRepository
from .repositories.statement import StatementRepository


@dataclass
class FinancialTimePoint:
    """時系列上の1点（1決算期分）."""

    fiscal_year: Optional[int]
    fiscal_period: Optional[str]  # 'FY', 'Q1', 'Q2', 'Q3'
    period_end: Optional[date]
    net_sales: Optional[float]
    operating_income: Optional[float]
    ordinary_income: Optional[float]
    net_income: Optional[float]
    eps: Optional[float]


def get_financial_history(
    ticker: str,
    years: int = 5,
    dsn: Optional[str] = None,
) -> list[FinancialTimePoint]:
    """指定銘柄の過去N年分の財務データを取得.

    Args:
        ticker: 証券コード（例: "7203"）
        years: 取得する年数（デフォルト: 5年）
        dsn: PostgreSQL 接続文字列（省略時は環境変数から取得）

    Returns:
        財務時系列データのリスト（period_end 降順）

    Example:
        >>> history = get_financial_history("7203", years=5)
        >>> for point in history:
        ...     print(f"{point.fiscal_year}: 売上 {point.net_sales:,}")
    """
    company_repo = CompanyRepository(dsn)
    filing_repo = FilingRepository(dsn)
    statement_repo = StatementRepository(dsn)

    # 会社を検索
    company = company_repo.find_by_ticker(ticker)
    if not company:
        return []

    # 本決算（FY）の Filing を取得
    filings = filing_repo.list_annual_filings(company.id, years=years)
    if not filings:
        return []

    # 各 Filing から財務データを組み立て
    result: list[FinancialTimePoint] = []
    for filing in filings:
        summary = statement_repo.get_financial_summary(filing.id)
        result.append(
            FinancialTimePoint(
                fiscal_year=filing.fiscal_year,
                fiscal_period=filing.fiscal_period,
                period_end=filing.period_end,
                net_sales=summary.get("net_sales"),
                operating_income=summary.get("operating_income"),
                ordinary_income=summary.get("ordinary_income"),
                net_income=summary.get("net_income"),
                eps=summary.get("eps"),
            )
        )

    return result


def get_financial_history_by_edinet_code(
    edinet_code: str,
    years: int = 5,
    dsn: Optional[str] = None,
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

    # 会社を検索
    company = company_repo.find_by_edinet_code(edinet_code)
    if not company:
        return []

    # 本決算（FY）の Filing を取得
    filings = filing_repo.list_annual_filings(company.id, years=years)
    if not filings:
        return []

    # 各 Filing から財務データを組み立て
    result: list[FinancialTimePoint] = []
    for filing in filings:
        summary = statement_repo.get_financial_summary(filing.id)
        result.append(
            FinancialTimePoint(
                fiscal_year=filing.fiscal_year,
                fiscal_period=filing.fiscal_period,
                period_end=filing.period_end,
                net_sales=summary.get("net_sales"),
                operating_income=summary.get("operating_income"),
                ordinary_income=summary.get("ordinary_income"),
                net_income=summary.get("net_income"),
                eps=summary.get("eps"),
            )
        )

    return result


def get_all_periods_history(
    ticker: str,
    years: int = 5,
    fiscal_period: Optional[str] = None,
    dsn: Optional[str] = None,
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

    result: list[FinancialTimePoint] = []
    for filing in filings:
        summary = statement_repo.get_financial_summary(filing.id)
        result.append(
            FinancialTimePoint(
                fiscal_year=filing.fiscal_year,
                fiscal_period=filing.fiscal_period,
                period_end=filing.period_end,
                net_sales=summary.get("net_sales"),
                operating_income=summary.get("operating_income"),
                ordinary_income=summary.get("ordinary_income"),
                net_income=summary.get("net_income"),
                eps=summary.get("eps"),
            )
        )

    return result


__all__ = [
    "FinancialTimePoint",
    "get_financial_history",
    "get_financial_history_by_edinet_code",
    "get_all_periods_history",
]
