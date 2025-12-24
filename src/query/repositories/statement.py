"""Statement（財務諸表）のリポジトリ."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ._base import BaseRepository


@dataclass
class StatementItemInfo:
    """財務諸表の項目情報."""

    id: int
    statement_id: int
    item_key: str
    label_ja: Optional[str]
    value_numeric: Optional[float]
    order_index: Optional[int]


class StatementRepository(BaseRepository):
    """Statement（財務諸表）へのアクセスを提供."""

    def get_items_by_filing(
        self,
        filing_id: int,
        statement_type: Optional[str] = None,
    ) -> list[StatementItemInfo]:
        """Filing IDから財務項目を取得.

        Args:
            filing_id: Filing ID
            statement_type: ステートメント種別（'PL', 'BS', 'CF'）。None の場合は全て

        Returns:
            財務項目のリスト
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT si.id, si.statement_id, si.item_key, si.label_ja,
                           si.value_numeric, si.order_index
                    FROM statement_items si
                    JOIN statements s ON s.id = si.statement_id
                    WHERE s.filing_id = %s
                """
                params: list = [filing_id]

                if statement_type:
                    base_query += " AND s.statement_type = %s"
                    params.append(statement_type)

                base_query += " ORDER BY s.statement_type, si.order_index"

                cur.execute(base_query, params)
                rows = cur.fetchall()
                return [
                    StatementItemInfo(
                        id=row[0],
                        statement_id=row[1],
                        item_key=row[2],
                        label_ja=row[3],
                        value_numeric=row[4],
                        order_index=row[5],
                    )
                    for row in rows
                ]

    def get_pl_items(self, filing_id: int) -> list[StatementItemInfo]:
        """Filing IDから損益計算書の項目を取得.

        Args:
            filing_id: Filing ID

        Returns:
            PL項目のリスト
        """
        return self.get_items_by_filing(filing_id, statement_type="PL")

    def get_bs_items(self, filing_id: int) -> list[StatementItemInfo]:
        """Filing IDから貸借対照表の項目を取得.

        Args:
            filing_id: Filing ID

        Returns:
            BS項目のリスト
        """
        return self.get_items_by_filing(filing_id, statement_type="BS")

    def get_cf_items(self, filing_id: int) -> list[StatementItemInfo]:
        """Filing IDからキャッシュフロー計算書の項目を取得.

        Args:
            filing_id: Filing ID

        Returns:
            CF項目のリスト
        """
        return self.get_items_by_filing(filing_id, statement_type="CF")

    def get_item_value(
        self,
        filing_id: int,
        item_key: str,
        statement_type: str = "PL",
    ) -> Optional[float]:
        """Filing IDと項目キーから値を取得.

        Args:
            filing_id: Filing ID
            item_key: 項目キー（例: 'net_sales', 'eps'）
            statement_type: ステートメント種別

        Returns:
            数値。見つからない場合は None
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT si.value_numeric
                    FROM statement_items si
                    JOIN statements s ON s.id = si.statement_id
                    WHERE s.filing_id = %s
                      AND s.statement_type = %s
                      AND si.item_key = %s
                    """,
                    (filing_id, statement_type, item_key),
                )
                row = cur.fetchone()
                if row:
                    return row[0]
        return None

    def get_financial_summary(self, filing_id: int) -> dict[str, Optional[float]]:
        """Filing IDから主要財務指標を辞書で取得.

        Args:
            filing_id: Filing ID

        Returns:
            主要指標の辞書（net_sales, operating_income, net_income, eps）
        """
        items = self.get_pl_items(filing_id)
        result: dict[str, Optional[float]] = {
            "net_sales": None,
            "operating_income": None,
            "ordinary_income": None,
            "net_income": None,
            "eps": None,
        }
        for item in items:
            if item.item_key in result:
                result[item.item_key] = item.value_numeric
        return result
