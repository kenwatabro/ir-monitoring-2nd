"""ダウンローダーの軽量ファクトリー."""

from __future__ import annotations

from datetime import date

from src.downloader._base import BaseDownloader
from src.downloader.edinet.downloader import EdinetDownloader

_downloaders: dict[str, type[BaseDownloader]] = {
    "edinet": EdinetDownloader,
    # "tdnet": TdnetDownloader,  # 将来追加
}


def get_downloader(source: str, start_date: date, end_date: date) -> BaseDownloader:
    """データソース名からダウンローダーを取得.

    Args:
        source: データソース名 ("edinet", "tdnet" など)
        start_date: 取得開始日
        end_date: 取得終了日

    Returns:
        対応するダウンローダーインスタンス

    Raises:
        KeyError: 未対応のデータソースの場合
    """
    if source not in _downloaders:
        available = ", ".join(_downloaders.keys())
        raise KeyError(f"Unknown source: {source}. Available: {available}")
    return _downloaders[source](start_date, end_date)


def list_sources() -> list[str]:
    """利用可能なデータソース一覧を返す."""
    return list(_downloaders.keys())
