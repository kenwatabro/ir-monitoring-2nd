"""EDINET XBRL パーサー用の共通ユーティリティ."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, List, Optional
import xml.etree.ElementTree as ET
import zipfile

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


def collect_facts_from_zip(zip_path: Path | str, limit: Optional[int] = None) -> List[XbrlFact]:
    """ZIPから fact を全件、または limit 件だけリストに詰めて返す。"""
    facts: List[XbrlFact] = []
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


def is_current_nonconsolidated(context_ref: Optional[str]) -> bool:
    """当期・単体（NonConsolidated）を表す contextRef かどうかの簡易判定。"""
    if context_ref is None:
        return False
    return context_ref.startswith("CurrentYear") and "NonConsolidatedMember" in context_ref


def pick_current_value(df: pd.DataFrame, local_names: List[str]) -> Optional[float]:
    """指定された local_name 候補から、当期・単体の値を1つ選んで返す."""
    if df.empty:
        return None

    candidates = df[df["local_name"].isin(local_names)].copy()
    if candidates.empty:
        return None

    preferred = candidates[candidates["context_ref"].map(is_current_nonconsolidated)]
    if preferred.empty:
        preferred = candidates[candidates["context_ref"].fillna("").str.contains("CurrentYear")]
    if preferred.empty:
        return None

    value_str = preferred.iloc[0]["value"]
    try:
        return float(value_str) if value_str is not None else None
    except (TypeError, ValueError):
        return None


def pick_instant_value(df: pd.DataFrame, local_names: List[str], context_keyword: str) -> Optional[float]:
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

    preferred = candidates[candidates["context_ref"].fillna("").str.contains(context_keyword)]
    if preferred.empty:
        return None

    value_str = preferred.iloc[0]["value"]
    try:
        return float(value_str) if value_str is not None else None
    except (TypeError, ValueError):
        return None


__all__ = [
    "find_instance_xbrl_name",
    "iter_facts_from_zip",
    "collect_facts_from_zip",
    "facts_to_dataframe",
    "add_local_name_column",
    "is_current_nonconsolidated",
    "pick_current_value",
    "pick_instant_value",
]


