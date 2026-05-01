"""src/parser/edinet/utils.py の単体テスト."""

from __future__ import annotations

import pandas as pd

from src.parser.edinet.utils import (
    add_local_name_column,
    pick_current_value,
    pick_instant_value,
)


def _make_df(rows: list[dict]) -> pd.DataFrame:
    base = {"tag": "", "context_ref": None, "unit_ref": None, "decimals": None, "value": None}
    return pd.DataFrame([{**base, **r} for r in rows])


class TestPickCurrentValue:
    def test_returns_none_on_empty_df(self) -> None:
        assert pick_current_value(pd.DataFrame(), ["NetSales"]) is None

    def test_returns_none_when_no_matching_local_name(self) -> None:
        df = add_local_name_column(_make_df([{"tag": "{ns}Other", "context_ref": "CurrentYear", "value": "100"}]))
        assert pick_current_value(df, ["NetSales"]) is None

    def test_picks_consolidated_over_nonconsolidated(self) -> None:
        df = add_local_name_column(
            _make_df(
                [
                    {"tag": "{ns}NetSales", "context_ref": "CurrentYearNonConsolidated", "value": "200"},
                    {"tag": "{ns}NetSales", "context_ref": "CurrentYearConsolidated", "value": "300"},
                ]
            )
        )
        assert pick_current_value(df, ["NetSales"]) == 300.0

    def test_falls_back_to_nonconsolidated_when_no_consolidated(self) -> None:
        df = add_local_name_column(
            _make_df(
                [
                    {"tag": "{ns}NetSales", "context_ref": "CurrentYearNonConsolidated", "value": "500"},
                ]
            )
        )
        assert pick_current_value(df, ["NetSales"]) == 500.0

    def test_skips_empty_value_rows(self) -> None:
        df = add_local_name_column(
            _make_df(
                [
                    {"tag": "{ns}NetSales", "context_ref": "CurrentYear", "value": ""},
                    {"tag": "{ns}NetSales", "context_ref": "CurrentYearNonConsolidated", "value": "400"},
                ]
            )
        )
        assert pick_current_value(df, ["NetSales"]) == 400.0

    def test_respects_local_names_priority_order(self) -> None:
        df = add_local_name_column(
            _make_df(
                [
                    {"tag": "{ns}OperatingRevenue", "context_ref": "CurrentYear", "value": "999"},
                    {"tag": "{ns}NetSales", "context_ref": "CurrentYear", "value": "111"},
                ]
            )
        )
        # NetSales が先頭なので NetSales を優先
        assert pick_current_value(df, ["NetSales", "OperatingRevenue"]) == 111.0
        # OperatingRevenue が先頭なので OperatingRevenue を優先
        assert pick_current_value(df, ["OperatingRevenue", "NetSales"]) == 999.0

    def test_returns_none_for_non_numeric_value(self) -> None:
        df = add_local_name_column(
            _make_df(
                [
                    {"tag": "{ns}NetSales", "context_ref": "CurrentYear", "value": "N/A"},
                ]
            )
        )
        assert pick_current_value(df, ["NetSales"]) is None


class TestPickInstantValue:
    def test_returns_none_on_empty_df(self) -> None:
        assert pick_instant_value(pd.DataFrame(), ["TotalAssets"], "CurrentYearInstant") is None

    def test_picks_matching_context(self) -> None:
        df = add_local_name_column(
            _make_df(
                [
                    {"tag": "{ns}TotalAssets", "context_ref": "CurrentYearInstant", "value": "1000"},
                    {"tag": "{ns}TotalAssets", "context_ref": "Prior1YearInstant", "value": "900"},
                ]
            )
        )
        assert pick_instant_value(df, ["TotalAssets"], "CurrentYearInstant") == 1000.0
        assert pick_instant_value(df, ["TotalAssets"], "Prior1YearInstant") == 900.0

    def test_skips_empty_values(self) -> None:
        df = add_local_name_column(
            _make_df(
                [
                    {"tag": "{ns}TotalAssets", "context_ref": "CurrentYearInstant", "value": "  "},
                ]
            )
        )
        assert pick_instant_value(df, ["TotalAssets"], "CurrentYearInstant") is None
