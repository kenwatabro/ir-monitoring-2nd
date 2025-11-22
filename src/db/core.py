"""PostgreSQL 接続用のシンプルなヘルパー."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg2
from psycopg2.extensions import connection as PgConnection


DEFAULT_PGURL = "postgresql://ir_user:ir_password@localhost:5432/ir_monitoring"


def get_pg_dsn(explicit_dsn: Optional[str] = None) -> str:
    """接続文字列を返す。

    優先順位:
        1. 引数で渡された dsn
        2. 環境変数 PGURL
        3. ローカル開発用のデフォルト
    """
    if explicit_dsn:
        return explicit_dsn
    env = os.getenv("PGURL")
    if env:
        return env
    return DEFAULT_PGURL


@contextmanager
def get_connection(dsn: Optional[str] = None) -> Iterator[PgConnection]:
    """PostgreSQLコネクションを contextmanager で提供する."""
    conn = psycopg2.connect(get_pg_dsn(dsn))
    try:
        yield conn
    finally:
        conn.close()



