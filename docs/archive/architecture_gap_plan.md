# Architecture Gap Analysis & Update Plan

`docs/architecture.md`（2024-12 更新）は Phase 1〜4 までのターゲット構成を定義しているが、実装状況を振り返ると複数の主要コンポーネントが未着手のまま残っている。本書は「何が欠落しているか」「どの順序で補完するか」を即時着手できる粒度で整理する。

---

## 1. 現状と乖離ポイント

| Architecture.md 節 | 設計上の期待 | 現在のリポジトリ状況 | ギャップ |
|--------------------|---------------|------------------------|-----------|
| §2.2 Directory Structure | `downloader/edinet/`, `parser/factory.py`, `ingest/factory.py`, etc. | `src/downloader/edinet_downloader.py` などファイル直置き | サブディレクトリ分割と Factory 群が存在しない |
| §3 Phase 1 | `src/query/repositories/*`, `src/query/timeseries.py` | `src/query/metrics/` が空、Repository 実装なし | DB 取得ロジックがバラバラに散在、共有 API 不在 |
| §3 Phase 2 | `src/reports/generators/company.py`, `scripts/show_company_report.py`, formatters | `src/reports/` 自体が存在しない | レポート出力パイプラインが未実装 |
| §3 Phase 3 | `src/analytics/screeners`, registry, CLI | `src/analytics/` ディレクトリなし | スクリーニング機構未着手 |
| §3 Phase 4 | Downloader/Parser/Ingest のサブディレクトリ移動 + Factory 完備 | 現状維持 | Phase 4 のリファクタに未着手 |
| §6 Next Actions | チェックリスト (5 items) | 進捗更新なし | ステータス追跡ができていない |

---

## 2. 更新ロードマップ

### Phase 1 (Repositories + Timeseries)
1. `src/query/repositories/_base.py` を作成し、`get_connection()` から psycopg2 connection を受け取る抽象クラスを定義。
2. `company.py`, `filing.py`, `statement.py` を追加し、既存の生 SQL 呼び出し箇所（`src/ingest/edinet_loader.py` など）を Repository に移動。
3. `src/query/timeseries.py` で `get_financial_history(ticker: str, years: int = 5)` を実装し、Repository を通じて EPS/売上等の系列を組み立てる。
4. `tests/unit/query/test_timeseries.py` を追加し、Repository をスタブ化して境界テストを行う。
5. `docs/architecture.md` の Phase 1 セクションに「完了条件」「最終コミット ID」を追記する。

### Phase 2 (Reports + CLI)
1. `src/reports/formatters/{__init__, _base, console, csv, markdown}.py` を作成し、`BaseFormatter.format(data: FinancialHistory)` を定義。
2. `src/reports/generators/company.py` の `CompanyReportGenerator` を実装し、timeseries API を呼び出して整形。
3. CLI: `scripts/show_company_report.py` を追加し、`argparse` から `--format` を受けて Formatter を切り替える。
4. `docs/architecture.md` Phase 2 に CLI 利用例と expected output サンプルを追加。

### Phase 3 (Screeners)
1. `src/analytics/registry.py` と `src/analytics/screeners/_base.py` を追加。`registry.register(name)(cls)` デコレータで自動登録できるようにする。
2. 最低 2 種類のスクリーン (`growth_margin.py`, `dividend_stable.py` など) を `src/analytics/screeners/` に実装。
3. `scripts/run_screener.py` を追加し、`--name` でレジストリから Screener を呼び出す CLI を実現。
4. `tests/unit/analytics/test_registry.py` と screener ごとの検証を追加。
5. Architecture ドキュメントにスクリーナー追加手順を追記。

### Phase 4 (Downloader/Parser/Ingest Reorg)
1. `src/downloader/edinet/` 配下へ `edinet_downloader.py` を移動し、`__init__.py` と `factory.py` を整える。
2. Parser, Ingest も同様にサブディレクトリ化して `factory.py` を共通 API (`get_parser(source: str)`) で公開。
3. 既存 import を全て新ディレクトリ構造に合わせて修正 (`runner.py`, `tests/`, `scripts/` 等)。
4. `docs/architecture.md` の §2.2 図を最新ディレクトリに更新し、差分を履歴に残す。

---

## 3. クロスカッティング作業

1. **テストと CI**  
   - Architecture にはテスト戦略の記述がないため、`docs/testing_strategy.md` を新設して `make test/unit`, `make test/integration` の前提や Docker 依存を明示する。  
   - GitHub Actions (または同等) を追加し、上記 make タスクを自動実行する。

2. **ドキュメント版管理**  
   - `docs/architecture.md` 冒頭に `Version` と `対応コミット` を記載し、更新時は `docs/CHANGELOG.md` にも追記。

3. **移行のトラッキング**  
   - `docs/architecture_progress.md`（チェックリスト）を作成し、Phase ごとに TODO/DOING/DONE を管理する。  
   - Issue テンプレート (`.github/ISSUE_TEMPLATE/architecture.md`) を作り、ドキュメント更新時に使用する。

---

## 4. 実装開始のための作業順序
1. `make install-dev` で開発環境を整備し、`make lint` が失敗する箇所を洗い出しておく。  
2. Phase 1〜2 を 1 PR、Phase 3 以降を追加 PR として段階的にマージし、`docs/architecture_progress.md` を PR ごとに更新する。  
3. 各 PR では「コード + テスト + ドキュメント」を必ずセットで更新し、Architecture に対して差分説明を付ける。

---

## 5. 期待される成果
- Architecture ドキュメントと実装の乖離がなくなり、開発者が `docs/architecture_progress.md` だけで作業状況を把握できる。  
- Repository/Timeseries/Reports/Screeners が段階的に導入され、銘柄分析フローが `downloader → parser → ingest → query → report → analytics` で一貫する。  
- Phase 4 のリファクタにより新データソース追加のコストが下がり、Architecture で想定された拡張性を得られる。
