"""EDINET XBRL から各種サマリー（PL/CF/BSなど）を抽出するパーサー."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from ._base import BaseSummary
from . import utils
from ..configs import load_edinet_config


@dataclass(slots=True)
class FinancialSummary(BaseSummary):
    """売上高・経常利益・当期純利益・EPS などの決算サマリー."""

    net_sales: Optional[float] = None
    operating_income: Optional[float] = None
    ordinary_income: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None

    @classmethod
    def parse_zip(cls, zip_path: Path | str) -> "FinancialSummary":
        """EDINETのXBRL ZIPから FinancialSummary を抽出するエントリポイント。"""
        facts = utils.collect_facts_from_zip(zip_path)
        df = utils.facts_to_dataframe(facts)
        return cls.from_dataframe(df)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "FinancialSummary":
        """すでにfact一覧を持っている DataFrame からサマリーを生成する."""
        if df.empty:
            return cls()

        df = utils.add_local_name_column(df)

        config = load_edinet_config().get("financial", {}).get("fields", {})

        def _pick(field_name: str) -> Optional[float]:
            spec = config.get(field_name)
            if not spec:
                return None
            mode = spec.get("mode")
            local_names = spec.get("local_names", [])
            if mode == "current":
                return utils.pick_current_value(df, local_names)
            if mode == "instant_current":
                return utils.pick_instant_value(df, local_names, "CurrentYearInstant")
            if mode == "instant_prior1":
                return utils.pick_instant_value(df, local_names, "Prior1YearInstant")
            return None

        return cls(
            net_sales=_pick("net_sales"),
            operating_income=_pick("operating_income"),
            ordinary_income=_pick("ordinary_income"),
            net_income=_pick("net_income"),
            eps=_pick("eps"),
        )


@dataclass(slots=True)
class CashFlowSummary(BaseSummary):
    """キャッシュ・フロー計算書の主要項目サマリー（ひな型）。

    具体的なマッピングは今後の検討に委ねる。
    """

    operating_cf: Optional[float] = None
    investing_cf: Optional[float] = None
    financing_cf: Optional[float] = None
    net_change_in_cash: Optional[float] = None
    cash_and_equivalents_begin: Optional[float] = None
    cash_and_equivalents_end: Optional[float] = None

    @classmethod
    def parse_zip(cls, zip_path: Path | str) -> "CashFlowSummary":
        """EDINETのXBRL ZIPから CF サマリを抽出するエントリポイント。"""
        facts = utils.collect_facts_from_zip(zip_path)
        df = utils.facts_to_dataframe(facts)
        return cls.from_dataframe(df)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "CashFlowSummary":
        """すでにfact一覧を持っている DataFrame から CFサマリを生成する."""
        if df.empty:
            return cls()

        df = utils.add_local_name_column(df)
        config = load_edinet_config().get("cash_flow", {}).get("fields", {})

        def _pick(field_name: str) -> Optional[float]:
            spec = config.get(field_name)
            if not spec:
                return None
            mode = spec.get("mode")
            local_names = spec.get("local_names", [])
            if mode == "current":
                return utils.pick_current_value(df, local_names)
            if mode == "instant_current":
                return utils.pick_instant_value(df, local_names, "CurrentYearInstant")
            if mode == "instant_prior1":
                return utils.pick_instant_value(df, local_names, "Prior1YearInstant")
            return None

        return cls(
            operating_cf=_pick("operating_cf"),
            investing_cf=_pick("investing_cf"),
            financing_cf=_pick("financing_cf"),
            net_change_in_cash=_pick("net_change_in_cash"),
            cash_and_equivalents_begin=_pick("cash_and_equivalents_begin"),
            cash_and_equivalents_end=_pick("cash_and_equivalents_end"),
        )


@dataclass(slots=True)
class BalanceSheetSummary(BaseSummary):
    """貸借対照表の主要項目サマリー."""

    # 資産サイド
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    noncurrent_assets: Optional[float] = None
    cash_and_deposits: Optional[float] = None

    # 負債サイド
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    noncurrent_liabilities: Optional[float] = None

    # 純資産サイド
    net_assets: Optional[float] = None
    shareholders_equity: Optional[float] = None

    # 指標系
    equity_ratio: Optional[float] = None
    net_assets_per_share: Optional[float] = None

    @classmethod
    def parse_zip(cls, zip_path: Path | str) -> "BalanceSheetSummary":
        """EDINETのXBRL ZIPから BS サマリを抽出するエントリポイント。"""
        facts = utils.collect_facts_from_zip(zip_path)
        df = utils.facts_to_dataframe(facts)
        return cls.from_dataframe(df)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "BalanceSheetSummary":
        """すでにfact一覧を持っている DataFrame から BSサマリを生成する."""
        if df.empty:
            return cls()

        df = utils.add_local_name_column(df)
        config = load_edinet_config().get("balance_sheet", {}).get("fields", {})

        def _pick(field_name: str) -> Optional[float]:
            spec = config.get(field_name)
            if not spec:
                return None
            mode = spec.get("mode")
            local_names = spec.get("local_names", [])
            if mode == "current":
                return utils.pick_current_value(df, local_names)
            if mode == "instant_current":
                return utils.pick_instant_value(df, local_names, "CurrentYearInstant")
            if mode == "instant_prior1":
                return utils.pick_instant_value(df, local_names, "Prior1YearInstant")
            return None

        total_assets = _pick("total_assets")
        net_assets = _pick("net_assets")
        total_liabilities = _pick("total_liabilities")

        # 総負債がタグから取れない場合は「資産－純資産」で近似
        if total_liabilities is None and total_assets is not None and net_assets is not None:
            total_liabilities = total_assets - net_assets

        return cls(
            total_assets=total_assets,
            current_assets=_pick("current_assets"),
            noncurrent_assets=_pick("noncurrent_assets"),
            cash_and_deposits=_pick("cash_and_deposits"),
            total_liabilities=total_liabilities,
            current_liabilities=_pick("current_liabilities"),
            noncurrent_liabilities=_pick("noncurrent_liabilities"),
            net_assets=net_assets,
            shareholders_equity=_pick("shareholders_equity"),
            equity_ratio=_pick("equity_ratio"),
            net_assets_per_share=_pick("net_assets_per_share"),
        )


def extract_summary_metrics(zip_path: Path | str) -> Dict[str, Optional[float]]:
    """従来インターフェース互換の「決算サマリーを dict で返す」ラッパー。"""
    summary = FinancialSummary.parse_zip(zip_path)
    return summary.to_dict()


__all__ = [
    "FinancialSummary",
    "CashFlowSummary",
    "BalanceSheetSummary",
    "extract_summary_metrics",
]


