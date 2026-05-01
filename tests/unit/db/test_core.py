"""src/db/core.py の単体テスト."""

from __future__ import annotations

import pytest

from src.db.core import get_pg_dsn


class TestGetPgDsn:
    def test_explicit_dsn_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PGURL", "postgresql://other/db")
        monkeypatch.setenv("POSTGRES_HOST", "192.168.0.100")
        result = get_pg_dsn("postgresql://explicit/mydb")
        assert result == "postgresql://explicit/mydb"

    def test_pgurl_wins_over_postgres_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PGURL", "postgresql://pgurl-host/db")
        monkeypatch.setenv("POSTGRES_HOST", "192.168.0.100")
        result = get_pg_dsn()
        assert result == "postgresql://pgurl-host/db"

    def test_postgres_host_builds_dsn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PGURL", raising=False)
        monkeypatch.setenv("POSTGRES_HOST", "192.168.0.100")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("POSTGRES_DB", "ir_monitoring")
        monkeypatch.setenv("POSTGRES_USER", "ir_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
        result = get_pg_dsn()
        assert result == "postgresql://ir_user:secret@192.168.0.100:5433/ir_monitoring"

    def test_postgres_host_uses_default_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PGURL", raising=False)
        monkeypatch.setenv("POSTGRES_HOST", "db-host")
        monkeypatch.delenv("POSTGRES_PORT", raising=False)
        monkeypatch.delenv("POSTGRES_DB", raising=False)
        monkeypatch.delenv("POSTGRES_USER", raising=False)
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        result = get_pg_dsn()
        assert "5432" in result
        assert "db-host" in result

    def test_raises_when_no_env_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PGURL", raising=False)
        monkeypatch.delenv("POSTGRES_HOST", raising=False)
        with pytest.raises(RuntimeError, match="PGURL または POSTGRES_HOST"):
            get_pg_dsn()
