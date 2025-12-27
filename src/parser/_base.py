"""Parser 基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class BaseParser(ABC):
    """パーサーの基底クラス.

    すべてのパーサーはこのクラスを継承する。
    """

    @abstractmethod
    def parse_zip(self, zip_path: Path | str) -> Dict[str, Any]:
        """ZIPファイルをパースしてサマリーを返す.

        Args:
            zip_path: パース対象のZIPファイルパス

        Returns:
            パース結果の辞書
        """

    @abstractmethod
    def parse_file(self, file_path: Path | str) -> Dict[str, Any]:
        """ファイルをパースしてサマリーを返す.

        Args:
            file_path: パース対象のファイルパス

        Returns:
            パース結果の辞書
        """


