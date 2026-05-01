"""会社情報のリポジトリ."""

from __future__ import annotations

from dataclasses import dataclass

from ._base import BaseRepository


@dataclass
class CompanyInfo:
    """会社情報."""

    id: int
    edinet_code: str
    ticker: str | None
    name_jp: str
    name_en: str | None = None


class CompanyRepository(BaseRepository):
    """会社情報へのアクセスを提供."""

    def find_by_ticker(self, ticker: str) -> CompanyInfo | None:
        """証券コードで会社を検索.

        Args:
            ticker: 証券コード（例: "7203"）

        Returns:
            会社情報。見つからない場合は None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, edinet_code, ticker, name_jp, name_en
                    FROM companies
                    WHERE ticker = %s
                    """,
                    (ticker,),
                )
                row = cur.fetchone()
                if row:
                    return CompanyInfo(
                        id=row[0],
                        edinet_code=row[1],
                        ticker=row[2],
                        name_jp=row[3],
                        name_en=row[4],
                    )
        return None

    def find_by_edinet_code(self, code: str) -> CompanyInfo | None:
        """EDINETコードで会社を検索.

        Args:
            code: EDINETコード

        Returns:
            会社情報。見つからない場合は None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, edinet_code, ticker, name_jp, name_en
                    FROM companies
                    WHERE edinet_code = %s
                    """,
                    (code,),
                )
                row = cur.fetchone()
                if row:
                    return CompanyInfo(
                        id=row[0],
                        edinet_code=row[1],
                        ticker=row[2],
                        name_jp=row[3],
                        name_en=row[4],
                    )
        return None

    def find_by_id(self, company_id: int) -> CompanyInfo | None:
        """会社IDで会社を検索.

        Args:
            company_id: 会社ID

        Returns:
            会社情報。見つからない場合は None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, edinet_code, ticker, name_jp, name_en
                    FROM companies
                    WHERE id = %s
                    """,
                    (company_id,),
                )
                row = cur.fetchone()
                if row:
                    return CompanyInfo(
                        id=row[0],
                        edinet_code=row[1],
                        ticker=row[2],
                        name_jp=row[3],
                        name_en=row[4],
                    )
        return None

    def search_by_name(self, keyword: str, limit: int = 20) -> list[CompanyInfo]:
        """会社名で部分一致検索.

        Args:
            keyword: 検索キーワード
            limit: 最大取得件数

        Returns:
            マッチした会社情報のリスト
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, edinet_code, ticker, name_jp, name_en
                    FROM companies
                    WHERE name_jp ILIKE %s OR name_en ILIKE %s
                    ORDER BY name_jp
                    LIMIT %s
                    """,
                    (f"%{keyword}%", f"%{keyword}%", limit),
                )
                rows = cur.fetchall()
                return [
                    CompanyInfo(
                        id=row[0],
                        edinet_code=row[1],
                        ticker=row[2],
                        name_jp=row[3],
                        name_en=row[4],
                    )
                    for row in rows
                ]
