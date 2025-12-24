# アーキテクチャ設計方針

> 作成日: 2024-12
> 最終更新: 2024-12
> 目的: 銘柄ごとの売上高・EPS等の推移表示機能、および将来の複数データソース・多数スクリーニング機能を見据えた設計指針

---

## 1. 現状分析

### 1.1 既存構造の評価

現在の `src/` 構造はすでに適切な責務分離ができている：

```
src/
├── db/                 # DB接続ヘルパー
│   └── core.py         # get_connection() 等
├── downloader/         # データダウンロード
│   ├── _base.py        # BaseDownloader (ABC)
│   └── edinet_downloader.py
├── ingest/             # DB へのロード
│   ├── edinet_loader.py
│   └── edinet_metadata.py
├── parser/             # XBRLパース
│   ├── configs/        # edinet.yaml 等
│   └── edinet/
│       ├── xbrl_parser.py   # FinancialSummary, CashFlowSummary, BalanceSheetSummary
│       └── utils.py
└── query/              # ← ほぼ空。これを拡充する
    └── metrics/        # 空
```

**良い設計要素:**
- `BaseDownloader` による抽象化 → 新データソース追加時に拡張可能
- dataclass + `BaseSummary` による構造化されたサマリークラス
- YAML設定ファイルによるXBRLマッピングの柔軟性
- DDLでスタースキーマ的なスキーマ設計済み

### 1.2 設計判断の評価

| 提案 | 評価 | 理由 |
|------|------|------|
| Clean Architecture大規模リファクタ | ❌ 現時点では過剰 | 既存構造で十分責務分離できている。`domain/application/infrastructure` への分割は移行コストに見合わない |
| Factory Method（辞書ベース軽量版） | ✅ 導入 | 複数データソース対応時に統一インターフェースで扱える |
| Repository パターン | ✅ 導入 | `src/query/repositories/` としてDBアクセスを抽象化。責務別に分割 |
| Strategy パターン + Registry | ✅ 導入 | スクリーニング条件をプラガブルに。レジストリで自動発見・登録 |
| Postgres + SQLiteエクスポート | △ 将来検討 | 分析配布用にSQLiteへのエクスポートは有効な選択肢 |

---

## 2. 設計方針

### 2.1 基本原則

1. **1ファイル1クラス原則** - クラスの肥大化を構造的に防止
2. **サブディレクトリによる分類** - データソース別、スクリーナーカテゴリ別に整理
3. **レジストリパターン** - スクリーナーの動的発見・登録で拡張を容易に
4. **辞書ベース軽量ファクトリー** - データソースの統一インターフェース

### 2.2 ディレクトリ構造（拡張後）

```
src/
├── db/                         # [既存] DB接続
│
├── downloader/                 # [既存→リファクタ] データソースごとにサブディレクトリ化
│   ├── __init__.py
│   ├── _base.py                # BaseDownloader (既存)
│   ├── factory.py              # 🆕 辞書ベース軽量ファクトリー
│   ├── edinet/                 # ← edinet_downloader.py を移動
│   │   ├── __init__.py
│   │   └── downloader.py
│   └── [future_source]/        # 例: tdnet/, jpx_timely/ など
│       ├── __init__.py
│       └── downloader.py
│
├── parser/                     # [既存→拡張]
│   ├── __init__.py
│   ├── _base.py                # 🆕 BaseParser
│   ├── factory.py              # 🆕 辞書ベース軽量ファクトリー
│   ├── edinet/                 # [既存]
│   │   ├── __init__.py
│   │   ├── _base.py            # XbrlFact, BaseSummary (既存)
│   │   ├── configs/            # edinet.yaml 等
│   │   ├── xbrl_parser.py
│   │   └── utils.py
│   └── [future_source]/
│       └── ...
│
├── ingest/                     # [既存→拡張]
│   ├── __init__.py
│   ├── _base.py                # 🆕 BaseLoader
│   ├── factory.py              # 🆕 辞書ベース軽量ファクトリー
│   ├── edinet/                 # ← 既存ファイルを移動
│   │   ├── __init__.py
│   │   ├── loader.py           # ← edinet_loader.py
│   │   └── metadata.py         # ← edinet_metadata.py
│   └── [future_source]/
│       └── ...
│
├── query/                      # [拡充] リポジトリを複数ファイルに分割
│   ├── __init__.py
│   ├── repositories/           # ← repository.py を責務別に分割
│   │   ├── __init__.py         # from .company import CompanyRepository 等
│   │   ├── _base.py            # BaseRepository (共通ヘルパー)
│   │   ├── company.py          # 会社検索・取得
│   │   ├── filing.py           # filing一覧・取得
│   │   └── statement.py        # statement/items取得
│   └── timeseries.py           # 時系列データ取得
│
├── reports/                    # 🆕 レポート生成
│   ├── __init__.py
│   ├── formatters/
│   │   ├── __init__.py
│   │   ├── _base.py            # BaseFormatter
│   │   ├── console.py
│   │   ├── csv.py
│   │   └── markdown.py
│   └── generators/
│       ├── __init__.py
│       ├── _base.py            # BaseReportGenerator
│       └── company.py
│
└── analytics/                  # 🆕 分析・スクリーニング
    ├── __init__.py
    ├── registry.py             # 🔑 スクリーナー自動発見・登録
    │
    ├── screeners/              # カテゴリ別にサブディレクトリ化
    │   ├── __init__.py
    │   ├── _base.py            # BaseScreener
    │   │
    │   ├── growth/             # 成長系
    │   │   ├── __init__.py
    │   │   ├── eps_growth.py
    │   │   ├── revenue_growth.py
    │   │   └── operating_income_growth.py
    │   │
    │   ├── value/              # バリュー系
    │   │   ├── __init__.py
    │   │   ├── per.py
    │   │   ├── pbr.py
    │   │   └── dividend_yield.py
    │   │
    │   ├── quality/            # クオリティ系
    │   │   ├── __init__.py
    │   │   ├── roe.py
    │   │   ├── roa.py
    │   │   └── profit_margin.py
    │   │
    │   ├── momentum/           # モメンタム系
    │   │   ├── __init__.py
    │   │   ├── relative_strength.py
    │   │   └── price_trend.py
    │   │
    │   └── composite/          # 複合条件
    │       ├── __init__.py
    │       ├── and_screener.py
    │       ├── or_screener.py
    │       └── canslim.py
    │
    └── indicators/             # 指標計算（スクリーナーから利用）
        ├── __init__.py
        ├── _base.py            # BaseIndicator
        ├── eps.py
        ├── revenue.py
        └── profitability.py
```

---

## 3. 設計パターン詳細

### 3.1 辞書ベース軽量ファクトリー（データソース用）

複数のデータソースを統一インターフェースで扱うための軽量なファクトリー。
正式な Factory Method パターンではなく、辞書による簡易実装。

```python
# src/downloader/factory.py
"""ダウンローダーの軽量ファクトリー."""
from datetime import date
from typing import Dict, Type

from src.downloader._base import BaseDownloader
from src.downloader.edinet.downloader import EdinetDownloader
# from src.downloader.tdnet.downloader import TdnetDownloader  # 将来追加

_downloaders: Dict[str, Type[BaseDownloader]] = {
    "edinet": EdinetDownloader,
    # "tdnet": TdnetDownloader,  # 将来追加
}


def get_downloader(source: str, start_date: date, end_date: date) -> BaseDownloader:
    """データソース名からダウンローダーを取得.

    Args:
        source: データソース名 ("edinet", "tdnet" など)
        start_date: 取得開始日
        end_date: 取得終了日

    Returns:
        対応するダウンローダーインスタンス

    Raises:
        KeyError: 未対応のデータソースの場合
    """
    if source not in _downloaders:
        available = ", ".join(_downloaders.keys())
        raise KeyError(f"Unknown source: {source}. Available: {available}")
    return _downloaders[source](start_date, end_date)


def list_sources() -> list[str]:
    """利用可能なデータソース一覧を返す."""
    return list(_downloaders.keys())
```

**使用例:**

```python
from src.downloader.factory import get_downloader, list_sources

# 利用可能なソース確認
print(list_sources())  # ['edinet', 'tdnet', ...]

# ソース名でダウンローダー取得
downloader = get_downloader("edinet", start_date, end_date)
downloader.download(output_dir)
```

**パーサー・ローダーも同様のパターン:**

```python
# src/parser/factory.py
from src.parser._base import BaseParser

def get_parser(source: str) -> BaseParser:
    ...

# src/ingest/factory.py
from src.ingest._base import BaseLoader

def get_loader(source: str, dsn: str | None = None) -> BaseLoader:
    ...
```

### 3.2 レジストリパターン（スクリーナー用）

多数のスクリーナーを動的に発見・登録するための仕組み。

```python
# src/analytics/registry.py
"""スクリーナーの自動発見・登録機構."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
    from src.analytics.screeners._base import BaseScreener

logger = logging.getLogger(__name__)

_registry: Dict[str, Type[BaseScreener]] = {}


def register(name: str):
    """スクリーナーを登録するデコレータ.

    使用例:
        @register("eps_growth")
        class EPSGrowthScreener(BaseScreener):
            ...
    """
    def decorator(cls: Type[BaseScreener]) -> Type[BaseScreener]:
        if name in _registry:
            logger.warning("Overwriting screener: %s", name)
        _registry[name] = cls
        return cls
    return decorator


def get_screener(name: str) -> Type[BaseScreener]:
    """名前でスクリーナークラスを取得.

    Raises:
        KeyError: 未登録のスクリーナー名の場合
    """
    if name not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise KeyError(f"Unknown screener: {name}. Available: {available}")
    return _registry[name]


def list_screeners() -> list[str]:
    """登録済みスクリーナー名一覧."""
    return sorted(_registry.keys())


def auto_discover() -> None:
    """screeners/ 配下のモジュールを自動インポートして登録.

    アプリケーション起動時に一度だけ呼び出す。
    """
    from src.analytics import screeners

    for _, name, _ in pkgutil.walk_packages(
        screeners.__path__,
        screeners.__name__ + ".",
    ):
        try:
            importlib.import_module(name)
        except ImportError as e:
            logger.warning("Failed to import screener module %s: %s", name, e)
```

### 3.3 スクリーナー基底クラス

```python
# src/analytics/screeners/_base.py
"""スクリーナーの基底クラス."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ScreenerResult:
    """スクリーニング結果."""
    passed: bool
    score: float | None = None  # オプション: ランキング用スコア
    details: dict[str, Any] | None = None  # オプション: 詳細情報


class BaseScreener(ABC):
    """スクリーニング条件の基底クラス.

    すべてのスクリーナーはこのクラスを継承し、
    @register デコレータで登録する。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """スクリーナーの表示名."""

    @property
    @abstractmethod
    def description(self) -> str:
        """スクリーナーの説明."""

    @abstractmethod
    def evaluate(self, company_data: dict) -> ScreenerResult:
        """単一銘柄を評価.

        Args:
            company_data: 銘柄の財務データ等を含む辞書

        Returns:
            評価結果
        """

    def filter(self, companies: list[dict]) -> list[dict]:
        """条件に合う銘柄を抽出.

        Args:
            companies: 評価対象の銘柄リスト

        Returns:
            条件を満たした銘柄のリスト
        """
        return [c for c in companies if self.evaluate(c).passed]
```

### 3.4 スクリーナー実装例

```python
# src/analytics/screeners/growth/eps_growth.py
"""EPS成長率スクリーナー."""
from src.analytics.registry import register
from src.analytics.screeners._base import BaseScreener, ScreenerResult


@register("eps_growth")
class EPSGrowthScreener(BaseScreener):
    """EPS成長率でフィルタリング."""

    def __init__(
        self,
        min_growth_rate: float = 0.15,
        years: int = 3,
    ):
        """
        Args:
            min_growth_rate: 最低成長率（0.15 = 15%）
            years: 評価期間（年数）
        """
        self.min_growth_rate = min_growth_rate
        self.years = years

    @property
    def name(self) -> str:
        return "EPS成長率"

    @property
    def description(self) -> str:
        return f"過去{self.years}年のEPS成長率が{self.min_growth_rate:.0%}以上"

    def evaluate(self, company_data: dict) -> ScreenerResult:
        eps_history = company_data.get("eps_history", [])

        if len(eps_history) < self.years + 1:
            return ScreenerResult(passed=False, details={"reason": "データ不足"})

        old_eps = eps_history[-(self.years + 1)]
        new_eps = eps_history[-1]

        if old_eps is None or old_eps <= 0:
            return ScreenerResult(passed=False, details={"reason": "基準年EPSが無効"})

        growth_rate = (new_eps - old_eps) / old_eps
        passed = growth_rate >= self.min_growth_rate

        return ScreenerResult(
            passed=passed,
            score=growth_rate,
            details={"growth_rate": growth_rate, "old_eps": old_eps, "new_eps": new_eps},
        )
```

### 3.5 複合スクリーナー

```python
# src/analytics/screeners/composite/and_screener.py
"""複数条件をAND結合するスクリーナー."""
from src.analytics.screeners._base import BaseScreener, ScreenerResult


class AndScreener(BaseScreener):
    """複数のスクリーナーをAND条件で結合."""

    def __init__(self, *screeners: BaseScreener):
        if not screeners:
            raise ValueError("At least one screener required")
        self.screeners = screeners

    @property
    def name(self) -> str:
        names = [s.name for s in self.screeners]
        return " AND ".join(names)

    @property
    def description(self) -> str:
        return "以下の条件をすべて満たす: " + ", ".join(
            s.description for s in self.screeners
        )

    def evaluate(self, company_data: dict) -> ScreenerResult:
        results = [s.evaluate(company_data) for s in self.screeners]
        passed = all(r.passed for r in results)

        # スコアは各スクリーナーのスコアの平均（Noneは除外）
        scores = [r.score for r in results if r.score is not None]
        avg_score = sum(scores) / len(scores) if scores else None

        return ScreenerResult(
            passed=passed,
            score=avg_score,
            details={"sub_results": [r.details for r in results]},
        )
```

**使用例:**

```python
from src.analytics.registry import auto_discover, get_screener
from src.analytics.screeners.composite.and_screener import AndScreener

# 起動時に一度だけ呼び出し
auto_discover()

# 名前でスクリーナーを取得
EPSGrowthScreener = get_screener("eps_growth")
ROEScreener = get_screener("roe")
PERScreener = get_screener("per")

# 複合条件を構築
screener = AndScreener(
    EPSGrowthScreener(min_growth_rate=0.20, years=3),
    ROEScreener(min_roe=0.15),
    PERScreener(max_per=20),
)

# スクリーニング実行
qualified = screener.filter(all_companies)
```

---

## 4. フェーズ別実装計画

### Phase 1: 時系列クエリ機能 ✅ 完了

**目的:** 銘柄を指定して、過去の売上高・EPS等を時系列で取得できるようにする

**ステータス:** 完了（2024-12）

**完了条件:**
- [x] `src/query/repositories/_base.py` - BaseRepository 実装
- [x] `src/query/repositories/company.py` - CompanyRepository 実装
- [x] `src/query/repositories/filing.py` - FilingRepository 実装
- [x] `src/query/repositories/statement.py` - StatementRepository 実装
- [x] `src/query/timeseries.py` - get_financial_history 実装
- [x] `tests/unit/query/test_timeseries.py` - 境界テスト追加

**実装ファイル:**

#### `src/query/repositories/company.py`

```python
"""会社情報のリポジトリ."""
from dataclasses import dataclass
from typing import Optional

from src.db import get_connection


@dataclass
class CompanyInfo:
    id: int
    edinet_code: str
    ticker: Optional[str]
    name_jp: str


class CompanyRepository:
    """会社情報へのアクセスを提供."""

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn

    def find_by_ticker(self, ticker: str) -> Optional[CompanyInfo]:
        """証券コードで会社を検索."""
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, edinet_code, ticker, name_jp FROM companies WHERE ticker = %s",
                    (ticker,),
                )
                row = cur.fetchone()
                if row:
                    return CompanyInfo(*row)
        return None

    def find_by_edinet_code(self, code: str) -> Optional[CompanyInfo]:
        """EDINETコードで会社を検索."""
        ...

    def search_by_name(self, keyword: str, limit: int = 20) -> list[CompanyInfo]:
        """会社名で部分一致検索."""
        ...
```

#### `src/query/timeseries.py`

```python
"""銘柄の財務時系列データを取得する."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.query.repositories.company import CompanyRepository
from src.query.repositories.filing import FilingRepository
from src.query.repositories.statement import StatementRepository


@dataclass
class FinancialTimePoint:
    """時系列上の1点（1決算期分）."""
    fiscal_year: int
    fiscal_period: str  # 'FY', 'Q1', 'Q2', 'Q3'
    period_end: date
    net_sales: Optional[float]
    operating_income: Optional[float]
    net_income: Optional[float]
    eps: Optional[float]


def get_financial_history(
    ticker: str,
    years: int = 5,
) -> list[FinancialTimePoint]:
    """指定銘柄の過去N年分の財務データを取得."""
    company_repo = CompanyRepository()
    filing_repo = FilingRepository()
    statement_repo = StatementRepository()

    company = company_repo.find_by_ticker(ticker)
    if not company:
        return []

    filings = filing_repo.list_for_company(company.id, years=years)
    # ... 時系列データの組み立て ...
```

---

### Phase 2: レポート出力（Phase 1完了後）

**目的:** 取得した時系列データを人間が読める形式で出力する

```python
# src/reports/generators/company.py
"""銘柄別レポートの生成."""
from src.query.timeseries import get_financial_history
from src.reports.formatters._base import BaseFormatter
from src.reports.formatters.console import ConsoleFormatter


class CompanyReportGenerator:
    """銘柄別レポートを生成."""

    def __init__(self, formatter: BaseFormatter | None = None):
        self.formatter = formatter or ConsoleFormatter()

    def generate(self, ticker: str, years: int = 5) -> str:
        """銘柄の財務推移レポートを生成."""
        history = get_financial_history(ticker, years)
        return self.formatter.format(history)
```

#### CLI統合

```python
# scripts/show_company_report.py
"""銘柄のレポートを表示するCLIスクリプト."""
import argparse

from src.reports.generators.company import CompanyReportGenerator
from src.reports.formatters.console import ConsoleFormatter
from src.reports.formatters.csv import CsvFormatter
from src.reports.formatters.markdown import MarkdownFormatter

FORMATTERS = {
    "console": ConsoleFormatter,
    "csv": CsvFormatter,
    "markdown": MarkdownFormatter,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", help="証券コード (例: 7203)")
    parser.add_argument("--format", default="console", choices=FORMATTERS.keys())
    args = parser.parse_args()

    formatter = FORMATTERS[args.format]()
    generator = CompanyReportGenerator(formatter)
    print(generator.generate(args.ticker))
```

---

### Phase 3: スクリーニング機能

**目的:** 条件に合う銘柄を抽出する

1. `src/analytics/screeners/_base.py` - 基底クラス実装
2. `src/analytics/registry.py` - レジストリ実装
3. 各スクリーナーを1ファイル1クラスで実装
4. `scripts/run_screener.py` - CLI統合

---

### Phase 4: データソース追加（必要になったら）

1. 既存の `edinet_downloader.py` → `edinet/downloader.py` へ移動
2. `src/downloader/factory.py` 作成
3. 同様に `parser/`, `ingest/` もリファクタ
4. 新データソース用サブディレクトリ追加

---

## 5. 設計判断の記録

### 5.1 採用したパターン

| パターン | 適用箇所 | 理由 |
|----------|----------|------|
| 辞書ベース軽量ファクトリー | downloader, parser, ingest | 複数データソースを統一インターフェースで扱う。正式なFactory Methodは過剰 |
| レジストリ + デコレータ | screeners | 多数のスクリーナーを動的発見。新規追加時にregistry.pyを編集不要 |
| Strategy パターン | screeners | スクリーニング条件をプラガブルに。AndScreener等で組み合わせ可能 |
| Repository パターン | query/repositories | DBアクセスの抽象化。責務別に分割して肥大化防止 |

### 5.2 採用しなかった選択肢

| 選択肢 | 不採用理由 |
|--------|------------|
| `domain/application/infrastructure` 分離 | 現規模では過剰。既存構造で十分責務分離できている |
| 抽象 Repository インターフェース（ports） | 現状DBは1種類（PostgreSQL）。テスト時はDB直接利用で十分 |
| ORM（SQLAlchemy）導入 | 現状のpsycopg2直書きで十分シンプル |
| Abstract Factory | 辞書ベースの軽量ファクトリーで十分 |

### 5.3 将来導入を検討する条件

| 条件 | 導入するもの |
|------|-------------|
| テスト時のDB差し替えが必要になる | 抽象 Repository インターフェース（Protocol） |
| データソース生成ロジックが複雑化 | Factory Method への昇格 |
| 複雑なクエリが増える | ORM検討 |

---

## 6. 次のアクション

1. [x] `src/query/repositories/` ディレクトリ作成・基本実装 ← Phase 1 完了
2. [x] `src/query/timeseries.py` 実装 ← Phase 1 完了
3. [ ] `scripts/show_company_report.py` 作成 - 動作確認 ← Phase 2
4. [ ] `src/analytics/registry.py` + `screeners/_base.py` 実装 ← Phase 3
5. [ ] 既存の `edinet_*` ファイルをサブディレクトリへ移動（Phase 4）

---

## 参考リンク

- [kawasin73のブログ - AI に作らせる株式分析システム](https://kawasin73.hatenablog.com/entry/2025/11/20/224346)
- [本リポジトリ README](../README.md)
