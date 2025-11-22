"""DBユーティリティパッケージ.

現時点では PostgreSQL への接続ヘルパのみを提供する。
将来的にリポジトリ層やクエリヘルパなどを追加していく想定。
"""

from .core import get_connection, get_pg_dsn

__all__ = ["get_connection", "get_pg_dsn"]



