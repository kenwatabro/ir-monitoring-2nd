"""スクリーナーの基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ScreenerResult:
    """スクリーニング結果.

    Attributes:
        passed: 条件を満たしたかどうか
        score: ランキング用スコア（オプション）
        details: 詳細情報（オプション）
    """

    passed: bool
    score: Optional[float] = None
    details: dict[str, Any] = field(default_factory=dict)


class BaseScreener(ABC):
    """スクリーニング条件の基底クラス.

    すべてのスクリーナーはこのクラスを継承し、
    @register デコレータで登録する。

    Example:
        @register("my_screener")
        class MyScreener(BaseScreener):
            @property
            def name(self) -> str:
                return "マイスクリーナー"

            @property
            def description(self) -> str:
                return "条件の説明"

            def evaluate(self, company_data: dict) -> ScreenerResult:
                # 評価ロジック
                return ScreenerResult(passed=True)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """スクリーナーの表示名."""

    @property
    @abstractmethod
    def description(self) -> str:
        """スクリーナーの説明."""

    @abstractmethod
    def evaluate(self, company_data: dict[str, Any]) -> ScreenerResult:
        """単一銘柄を評価.

        Args:
            company_data: 銘柄の財務データ等を含む辞書
                - ticker: 証券コード
                - name: 会社名
                - eps_history: EPS履歴のリスト
                - net_sales_history: 売上高履歴のリスト
                - その他の財務指標

        Returns:
            評価結果
        """

    def filter(self, companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """条件に合う銘柄を抽出.

        Args:
            companies: 評価対象の銘柄リスト

        Returns:
            条件を満たした銘柄のリスト
        """
        return [c for c in companies if self.evaluate(c).passed]

    def rank(
        self, companies: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], ScreenerResult]]:
        """銘柄をスコア順にランク付け.

        Args:
            companies: 評価対象の銘柄リスト

        Returns:
            (銘柄データ, 評価結果) のタプルリスト（スコア降順）
        """
        results = [(c, self.evaluate(c)) for c in companies]
        # passed=True のみ、スコア降順でソート
        passed = [(c, r) for c, r in results if r.passed]
        return sorted(passed, key=lambda x: x[1].score or 0, reverse=True)
