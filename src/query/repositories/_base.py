"""Repository 基底クラス."""

from __future__ import annotations

from typing import Optional

from src.db import get_connection


class BaseRepository:
    """Repository の共通基底クラス.

    すべての Repository はこのクラスを継承し、
    DB接続を統一的に取得する。
    """

    def __init__(self, dsn: Optional[str] = None):
        """Initialize repository with optional DSN.

        Args:
            dsn: PostgreSQL 接続文字列（省略時は環境変数から取得）
        """
        self.dsn = dsn

    def _get_connection(self):
        """DB接続を取得する.

        Returns:
            psycopg2 connection context manager
        """
        return get_connection(self.dsn)


