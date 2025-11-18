"""EDINET XBRL パーサー用の共通モデル."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass(slots=True)
class XbrlFact:
    """単一の XBRL fact を表現する簡易モデル。"""

    tag: str
    context_ref: Optional[str]
    unit_ref: Optional[str]
    decimals: Optional[str]
    value: Optional[str]


@dataclass(slots=True)
class BaseSummary:
    """決算サマリ（PL/CF/BSなど）の共通親クラス."""

    def to_dict(self) -> Dict[str, Optional[float]]:
        """データクラスのフィールドをシンプルな dict に変換する共通ヘルパー。"""
        data = asdict(self)
        # ここでは値の型は Optional[float] を想定するが、厳密なチェックは行わない
        return data  # type: ignore[return-value]


__all__ = [
    "XbrlFact",
    "BaseSummary",
]


