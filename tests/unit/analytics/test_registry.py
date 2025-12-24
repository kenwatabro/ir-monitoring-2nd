"""Registry モジュールのテスト."""

from __future__ import annotations

import pytest

from src.analytics.registry import (
    auto_discover,
    clear_registry,
    get_screener,
    list_screeners,
    register,
)
from src.analytics.screeners._base import BaseScreener, ScreenerResult


class TestRegister:
    """register デコレータのテスト."""

    def setup_method(self) -> None:
        """各テスト前にレジストリをクリア."""
        clear_registry()

    def teardown_method(self) -> None:
        """各テスト後にレジストリをクリア."""
        clear_registry()

    def test_register_screener(self) -> None:
        """スクリーナーを登録できる."""

        @register("test_screener")
        class TestScreener(BaseScreener):
            @property
            def name(self) -> str:
                return "Test"

            @property
            def description(self) -> str:
                return "Test screener"

            def evaluate(self, company_data: dict) -> ScreenerResult:
                return ScreenerResult(passed=True)

        assert "test_screener" in list_screeners()
        assert get_screener("test_screener") is TestScreener

    def test_register_overwrites_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """同じ名前で再登録すると警告が出る."""

        @register("duplicate")
        class First(BaseScreener):
            @property
            def name(self) -> str:
                return "First"

            @property
            def description(self) -> str:
                return "First"

            def evaluate(self, company_data: dict) -> ScreenerResult:
                return ScreenerResult(passed=True)

        @register("duplicate")
        class Second(BaseScreener):
            @property
            def name(self) -> str:
                return "Second"

            @property
            def description(self) -> str:
                return "Second"

            def evaluate(self, company_data: dict) -> ScreenerResult:
                return ScreenerResult(passed=False)

        assert get_screener("duplicate") is Second
        assert "Overwriting screener: duplicate" in caplog.text


class TestGetScreener:
    """get_screener のテスト."""

    def setup_method(self) -> None:
        clear_registry()

    def teardown_method(self) -> None:
        clear_registry()

    def test_raises_key_error_for_unknown(self) -> None:
        """未登録のスクリーナーで KeyError."""
        with pytest.raises(KeyError) as exc_info:
            get_screener("unknown")
        assert "Unknown screener: unknown" in str(exc_info.value)


class TestAutoDiscover:
    """auto_discover のテスト."""

    def test_discovers_builtin_screeners(self) -> None:
        """組み込みスクリーナーを発見できる.

        Note: モジュールが既にインポートされている場合、importlib.import_module は
        再度デコレータを実行しない。そのため、このテストではモジュールを直接
        インポートしてデコレータを実行させる。
        """
        # モジュールを直接インポートしてデコレータを実行させる
        import src.analytics.screeners.growth.eps_growth  # noqa: F401
        import src.analytics.screeners.growth.revenue_growth  # noqa: F401
        import src.analytics.screeners.value.profit_margin  # noqa: F401

        auto_discover()

        screeners = list_screeners()
        assert "eps_growth" in screeners
        assert "revenue_growth" in screeners
        assert "profit_margin" in screeners


class TestListScreeners:
    """list_screeners のテスト."""

    def test_returns_sorted_list(self) -> None:
        """ソートされたリストを返す."""
        clear_registry()

        @register("z_screener")
        class ZScreener(BaseScreener):
            @property
            def name(self) -> str:
                return "Z"

            @property
            def description(self) -> str:
                return "Z"

            def evaluate(self, company_data: dict) -> ScreenerResult:
                return ScreenerResult(passed=True)

        @register("a_screener")
        class AScreener(BaseScreener):
            @property
            def name(self) -> str:
                return "A"

            @property
            def description(self) -> str:
                return "A"

            def evaluate(self, company_data: dict) -> ScreenerResult:
                return ScreenerResult(passed=True)

        screeners = list_screeners()
        assert screeners == ["a_screener", "z_screener"]
