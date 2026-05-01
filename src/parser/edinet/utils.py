"""EDINET XBRL パーサー用の共通ユーティリティ."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

import pandas as pd

from ._base import XbrlFact


def find_instance_xbrl_name(zf: zipfile.ZipFile) -> str:
    """ZIP内からインスタンスXBRLと思われるファイル名を1つ返す。

    現状は「拡張子 .xbrl の最初の1つ」を採用するシンプルな実装。
    """
    for name in zf.namelist():
        if name.lower().endswith(".xbrl"):
            return name
    raise FileNotFoundError("ZIP内に .xbrl ファイルが見つかりませんでした")


def iter_facts_from_zip(zip_path: Path | str) -> Iterator[XbrlFact]:
    """EDINETのXBRL一式ZIPから fact を順に yield するジェネレータ。"""
    path = Path(zip_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    with zipfile.ZipFile(path) as zf:
        xbrl_name = find_instance_xbrl_name(zf)
        with zf.open(xbrl_name) as fh:
            tree = ET.parse(fh)

    root = tree.getroot()
    for elem in root:
        if "contextRef" not in elem.attrib:
            continue
        yield XbrlFact(
            tag=elem.tag,
            context_ref=elem.attrib.get("contextRef"),
            unit_ref=elem.attrib.get("unitRef"),
            decimals=elem.attrib.get("decimals"),
            value=elem.text,
        )


def collect_facts_from_zip(zip_path: Path | str, limit: int | None = None) -> list[XbrlFact]:
    """ZIPから fact を全件、または limit 件だけリストに詰めて返す。"""
    facts: list[XbrlFact] = []
    for i, fact in enumerate(iter_facts_from_zip(zip_path)):
        facts.append(fact)
        if limit is not None and i + 1 >= limit:
            break
    return facts


def facts_to_dataframe(facts: Iterable[XbrlFact]) -> pd.DataFrame:
    """XbrlFact の列を pandas.DataFrame に変換するヘルパー。"""
    rows = [
        {
            "tag": f.tag,
            "context_ref": f.context_ref,
            "unit_ref": f.unit_ref,
            "decimals": f.decimals,
            "value": f.value,
        }
        for f in facts
    ]
    return pd.DataFrame(rows)


def add_local_name_column(df: pd.DataFrame, column: str = "local_name") -> pd.DataFrame:
    """`{namespace}LocalName` 形式のタグからローカル名列を追加する."""

    def _local_name(tag: str) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    df = df.copy()
    df[column] = df["tag"].map(_local_name)
    return df


def pick_current_value(df: pd.DataFrame, local_names: list[str]) -> float | None:
    """指定された local_name 候補から当期の値を1つ選んで返す.

    優先順位:
    1. 当期・連結（CurrentYear かつ NonConsolidated を含まない）
    2. 当期・単体（CurrentYear かつ NonConsolidated を含む）
    3. その他 CurrentYear コンテキスト

    日本の上場企業の多くは連結決算を主体とするため、連結を優先する。
    """
    if df.empty:
        return None

    candidates = df[df["local_name"].isin(local_names)].copy()
    if candidates.empty:
        return None

    # 空値行を除外（XBRLに空タグが残ることがあり、連結優先フィルタが空を拾うと取りこぼす）
    values = candidates["value"].fillna("").astype(str).str.strip()
    candidates = candidates[values != ""]
    if candidates.empty:
        return None

    ctx = candidates["context_ref"].fillna("")

    # 1. 連結・当期
    consolidated = candidates[ctx.str.contains("CurrentYear") & ~ctx.str.contains("NonConsolidated")]
    if not consolidated.empty:
        preferred = consolidated
    else:
        # 2. 単体・当期（連結タグがない企業向け）
        preferred = candidates[ctx.str.contains("CurrentYear")]

    if preferred.empty:
        return None

    # local_names の並び順を優先度とみなす（yaml で先頭ほど優先）
    name_order = {name: i for i, name in enumerate(local_names)}
    preferred = preferred.assign(_prio=preferred["local_name"].map(name_order).fillna(len(local_names))).sort_values(
        "_prio"
    )

    value_str = preferred.iloc[0]["value"]
    try:
        return float(value_str) if value_str is not None else None
    except (TypeError, ValueError):
        return None


def pick_instant_value(df: pd.DataFrame, local_names: list[str], context_keyword: str) -> float | None:
    """指定された local_name と context キーワードから、期首/期末などの値を1つ選んで返す。

    例:
    - context_keyword="CurrentYearInstant" -> 当期末残高
    - context_keyword="Prior1YearInstant" -> 前期末（=当期期首）残高
    """
    if df.empty:
        return None

    candidates = df[df["local_name"].isin(local_names)].copy()
    if candidates.empty:
        return None

    values = candidates["value"].fillna("").astype(str).str.strip()
    candidates = candidates[values != ""]
    if candidates.empty:
        return None

    preferred = candidates[candidates["context_ref"].fillna("").str.contains(context_keyword)]
    if preferred.empty:
        return None

    value_str = preferred.iloc[0]["value"]
    try:
        return float(value_str) if value_str is not None else None
    except (TypeError, ValueError):
        return None


def extract_zip_metadata(zip_path: Path | str) -> dict[str, str]:
    """XBRL ZIP から会社コード・社名・期間などのメタ情報を抽出する.

    Returns:
        edinet_code, company_name, security_code, period_start, period_end を含む dict。
        取得できなかったキーは空文字列。
    """
    meta: dict[str, str] = {
        "edinet_code": "",
        "company_name": "",
        "security_code": "",
        "period_start": "",
        "period_end": "",
    }

    try:
        with zipfile.ZipFile(zip_path) as zf:
            xbrl_name = find_instance_xbrl_name(zf)
            with zf.open(xbrl_name) as fh:
                tree = ET.parse(fh)
    except Exception:  # noqa: BLE001
        return meta

    root = tree.getroot()
    contexts: list[ET.Element] = [elem for elem in root if elem.tag.lower().endswith("context")]

    chosen_ctx: ET.Element | None = None
    for ctx in contexts:
        if "CurrentYear" in ctx.attrib.get("id", "") and ctx.find(".//{*}startDate") is not None:
            chosen_ctx = ctx
            break
    if chosen_ctx is None and contexts:
        chosen_ctx = contexts[0]

    if chosen_ctx is not None:
        ident = chosen_ctx.find(".//{*}identifier")
        if ident is not None and ident.text:
            meta["edinet_code"] = ident.text.strip()

        period = chosen_ctx.find(".//{*}period")
        if period is not None:
            start = period.find(".//{*}startDate")
            end = period.find(".//{*}endDate")
            instant = period.find(".//{*}instant")
            if start is not None and start.text:
                meta["period_start"] = start.text.strip()
            if end is not None and end.text:
                meta["period_end"] = end.text.strip()
            elif instant is not None and instant.text:
                meta["period_end"] = instant.text.strip()

    def _local(tag: str) -> str:
        return tag.split("}", 1)[1] if "}" in tag else tag

    for elem in root.iter():
        lname = _local(elem.tag)
        if not elem.text:
            continue
        text = elem.text.strip()

        if not meta["company_name"] and lname in (
            "CompanyNameCoverPage",
            "CompanyName",
            "CompanyNameDEI",
            "FundNameInJapaneseDEI",
            "FundNameCoverPage",
        ):
            meta["company_name"] = text

        if not meta["security_code"] and lname in (
            "SecurityCode",
            "SecurityCodeCoverPage",
            "SecurityCodeDEI",
        ):
            code = text.strip()
            # EDINETは5桁（末尾0付き）で格納する場合がある → 4桁に正規化
            if len(code) == 5 and code.endswith("0"):
                code = code[:4]
            meta["security_code"] = code

        if meta["company_name"] and meta["security_code"]:
            break

    return meta


__all__ = [
    "find_instance_xbrl_name",
    "iter_facts_from_zip",
    "collect_facts_from_zip",
    "facts_to_dataframe",
    "add_local_name_column",
    "pick_current_value",
    "pick_instant_value",
    "extract_zip_metadata",
]
