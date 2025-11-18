"""EDINET向けXBRLパーサー群。

基本的な構成:

- `_base.py` : 共通のモデル / 親クラス
- `utils.py` : ZIP展開やDataFrame変換などの補助関数
- `xbrl_parser.py` : 各種サマリクラスと、XBRL→サマリへの変換ロジック
"""

from ._base import XbrlFact, BaseSummary

__all__ = [
    "XbrlFact",
    "BaseSummary",
]


