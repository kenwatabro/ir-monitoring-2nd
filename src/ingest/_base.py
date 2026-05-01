"""Ingest/Loader 基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseLoader(ABC):
    """データローダーの基底クラス.

    すべてのローダーはこのクラスを継承する。
    """

    def __init__(self, dsn: str | None = None):
        """Initialize loader.

        Args:
            dsn: PostgreSQL 接続文字列（省略時は環境変数から取得）
        """
        self.dsn = dsn

    @abstractmethod
    def load_directory(self, source_dir: Path | str, max_files: int | None = None) -> None:
        """ディレクトリからデータをロードする.

        Args:
            source_dir: ソースディレクトリ
            max_files: 処理するファイル数の上限（デバッグ用）
        """
