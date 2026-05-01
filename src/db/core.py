"""PostgreSQL 接続用のシンプルなヘルパー."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as PgConnection

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_pg_dsn(explicit_dsn: str | None = None) -> str:
    """接続文字列を返す。

    優先順位:
        1. 引数で渡された dsn
        2. 環境変数 PGURL
        3. 環境変数 POSTGRES_HOST（+ PORT / DB / USER / PASSWORD）
    PGURL も POSTGRES_HOST も未設定の場合は例外を送出する。
    """
    if explicit_dsn:
        return explicit_dsn

    if pgurl := os.getenv("PGURL"):
        return pgurl

    host = os.getenv("POSTGRES_HOST")
    if host:
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "ir_monitoring")
        user = os.getenv("POSTGRES_USER", "ir_user")
        password = os.getenv("POSTGRES_PASSWORD", "")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    raise RuntimeError("DB接続先が未設定です。PGURL または POSTGRES_HOST を環境変数（.env）で指定してください。")


@contextmanager
def get_connection(dsn: str | None = None) -> Iterator[PgConnection]:
    """PostgreSQLコネクションを contextmanager で提供する."""
    conn = psycopg2.connect(get_pg_dsn(dsn))
    try:
        yield conn
    finally:
        conn.close()
