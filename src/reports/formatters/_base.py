"""Formatter 基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.query.timeseries import FinancialTimePoint


class BaseFormatter(ABC):
    """レポートフォーマッターの基底クラス.

    すべてのフォーマッターはこのクラスを継承し、
    format メソッドを実装する。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """フォーマッターの名前."""

    @abstractmethod
    def format(self, data: list[FinancialTimePoint], company_name: str = "") -> str:
        """財務時系列データをフォーマットする.

        Args:
            data: 財務時系列データのリスト
            company_name: 会社名（オプション）

        Returns:
            フォーマットされた文字列
        """

    def _format_number(self, value: float | None, unit: str = "") -> str:
        """数値をフォーマットする.

        Args:
            value: 数値（None の場合は "-"）
            unit: 単位（例: "百万円"）

        Returns:
            フォーマットされた文字列
        """
        if value is None:
            return "-"
        # 百万円単位に変換（1,000,000で割る）
        value_in_millions = value / 1_000_000
        return f"{value_in_millions:,.0f}{unit}"

    def _format_eps(self, value: float | None) -> str:
        """EPSをフォーマットする.

        Args:
            value: EPS値

        Returns:
            フォーマットされた文字列
        """
        if value is None:
            return "-"
        return f"{value:,.2f}"
