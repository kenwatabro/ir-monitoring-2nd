"""ローダーの軽量ファクトリー."""

from __future__ import annotations

from typing import Dict, Optional, Type

from src.ingest._base import BaseLoader
from src.ingest.edinet.loader import EdinetLoader

_loaders: Dict[str, Type[BaseLoader]] = {
    "edinet": EdinetLoader,
    # "tdnet": TdnetLoader,  # 将来追加
}


def get_loader(source: str, dsn: Optional[str] = None) -> BaseLoader:
    """データソース名からローダーを取得.

    Args:
        source: データソース名 ("edinet", "tdnet" など)
        dsn: PostgreSQL 接続文字列

    Returns:
        対応するローダーインスタンス

    Raises:
        KeyError: 未対応のデータソースの場合
    """
    if source not in _loaders:
        available = ", ".join(_loaders.keys())
        raise KeyError(f"Unknown source: {source}. Available: {available}")
    return _loaders[source](dsn)


def list_sources() -> list[str]:
    """利用可能なデータソース一覧を返す."""
    return list(_loaders.keys())


