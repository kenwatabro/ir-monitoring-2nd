"""Filing（提出書類）のリポジトリ."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ._base import BaseRepository


@dataclass
class FilingInfo:
    """提出書類情報."""

    id: int
    company_id: int
    edinet_doc_id: str
    period_start: date | None
    period_end: date | None
    fiscal_year: int | None
    fiscal_period: str | None  # 'FY', 'Q1', 'Q2', 'Q3'
    is_consolidated: bool


class FilingRepository(BaseRepository):
    """Filing（提出書類）へのアクセスを提供."""

    def find_by_id(self, filing_id: int) -> FilingInfo | None:
        """Filing IDで検索.

        Args:
            filing_id: Filing ID

        Returns:
            Filing情報。見つからない場合は None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, company_id, edinet_doc_id, period_start, period_end,
                           fiscal_year, fiscal_period, is_consolidated
                    FROM filings
                    WHERE id = %s
                    """,
                    (filing_id,),
                )
                row = cur.fetchone()
                if row:
                    return FilingInfo(
                        id=row[0],
                        company_id=row[1],
                        edinet_doc_id=row[2],
                        period_start=row[3],
                        period_end=row[4],
                        fiscal_year=row[5],
                        fiscal_period=row[6],
                        is_consolidated=row[7],
                    )
        return None

    def list_for_company(
        self,
        company_id: int,
        years: int = 5,
        fiscal_period: str | None = None,
    ) -> list[FilingInfo]:
        """会社IDから Filing 一覧を取得.

        Args:
            company_id: 会社ID
            years: 取得する年数（現在から過去N年分）
            fiscal_period: 期種別でフィルタ（'FY', 'Q1', 'Q2', 'Q3'）。None の場合は全て

        Returns:
            Filing情報のリスト（period_end 降順）
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT id, company_id, edinet_doc_id, period_start, period_end,
                           fiscal_year, fiscal_period, is_consolidated
                    FROM filings
                    WHERE company_id = %s
                      AND period_end >= CURRENT_DATE - make_interval(years => %s)
                """
                params: list = [company_id, years]

                if fiscal_period:
                    base_query += " AND fiscal_period = %s"
                    params.append(fiscal_period)

                base_query += " ORDER BY period_end DESC"

                cur.execute(base_query, params)
                rows = cur.fetchall()
                return [
                    FilingInfo(
                        id=row[0],
                        company_id=row[1],
                        edinet_doc_id=row[2],
                        period_start=row[3],
                        period_end=row[4],
                        fiscal_year=row[5],
                        fiscal_period=row[6],
                        is_consolidated=row[7],
                    )
                    for row in rows
                ]

    def list_annual_filings(self, company_id: int, years: int = 5) -> list[FilingInfo]:
        """会社IDから本決算（FY）の Filing 一覧を取得.

        同一会社・同一 period_end に複数 filing がある場合（訂正有報等）は
        edinet_doc_id が最大（= 最新提出）の1件のみを返す。

        Args:
            company_id: 会社ID
            years: 取得する年数

        Returns:
            本決算Filing情報のリスト（period_end 降順、期ごとに1件）
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (period_end)
                        id, company_id, edinet_doc_id, period_start, period_end,
                        fiscal_year, fiscal_period, is_consolidated
                    FROM filings
                    WHERE company_id = %s
                      AND fiscal_period = 'FY'
                      AND period_end >= CURRENT_DATE - make_interval(years => %s)
                    ORDER BY period_end DESC, edinet_doc_id DESC
                    """,
                    (company_id, years),
                )
                rows = cur.fetchall()
                return [
                    FilingInfo(
                        id=row[0],
                        company_id=row[1],
                        edinet_doc_id=row[2],
                        period_start=row[3],
                        period_end=row[4],
                        fiscal_year=row[5],
                        fiscal_period=row[6],
                        is_consolidated=row[7],
                    )
                    for row in rows
                ]

    def find_latest_for_company(self, company_id: int) -> FilingInfo | None:
        """会社IDから最新の Filing を取得.

        Args:
            company_id: 会社ID

        Returns:
            最新のFiling情報。見つからない場合は None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, company_id, edinet_doc_id, period_start, period_end,
                           fiscal_year, fiscal_period, is_consolidated
                    FROM filings
                    WHERE company_id = %s
                    ORDER BY period_end DESC
                    LIMIT 1
                    """,
                    (company_id,),
                )
                row = cur.fetchone()
                if row:
                    return FilingInfo(
                        id=row[0],
                        company_id=row[1],
                        edinet_doc_id=row[2],
                        period_start=row[3],
                        period_end=row[4],
                        fiscal_year=row[5],
                        fiscal_period=row[6],
                        is_consolidated=row[7],
                    )
        return None
