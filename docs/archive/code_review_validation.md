# Code Review Validation & Remediation Plan

## 1. 目的と対象
- 対象ファイル: `docs/code_review.md` のレビュー指摘（EDINET ダウンロード〜ロード処理、および解析基盤全体）
- 参照資料: Fluent Python 第2版、オブジェクト設計スタイルガイド、`docs/architecture.md`
- ゴール: 指摘の真偽を検証し、コードベースをどの順序で改修すればよいかを明文化する

---

## 2. 真偽確認の結果

### 2.1 正当と判断したレビュー指摘
| # | 内容 | 影響範囲 | 根拠 |
|---|------|----------|------|
| 1 | `EdinetDownloader` が secCode を受け取らず単一銘柄抽出という契約を守れていない | `src/downloader/edinet_downloader.py:1-48` | docstring と実装が乖離し、全銘柄をダウンロードしている |
| 2 | API キー未設定時に遅延失敗する | `src/downloader/edinet_downloader.py:28-58` | `os.getenv("EDINET_API_KEY")` の結果検証がない |
| 3 | `_infer_fiscal_info` が期別を誤分類 | `src/ingest/edinet_loader.py:101-124` | 12 月決算を Q3 として扱う等、不変条件違反 |
| 4 | 既存 filing を毎回フルスキャン | `src/ingest/edinet_loader.py:159-317` | 全件 `SELECT` により I/O が肥大化 |
| 5 | テストスイートが存在しない | ルート配下全体 | README が言及する `make test/*` が未整備 |

### 2.2 修正が必要なレビュー指摘
| # | 再評価結果 | 影響範囲 |
|---|------------|----------|
| A | 「XBRL の値取得が連結値を捨てる」という指摘は過剰。実際は単体優先ロジックが固定化されているだけ | `src/parser/edinet/utils.py:95-114` |

### 2.3 追加で判明した欠陥
| # | 内容 | 影響範囲 | 根拠 |
|---|------|----------|------|
| B | 既存 filing の再取り込みが無効 (`_get_existing_doc_ids` で全 ZIP をスキップ) | `src/ingest/edinet_loader.py:302-359` | UPDATE 分岐が一度も実行されない |
| C | `edinet_code` を取得できない ZIP がすべて `UNKNOWN` にマージされ `companies.edinet_code` の UNIQUE を壊す | `src/ingest/edinet_loader.py:323-333`, `ddl/001_core_financial_reporting.sql:6-15` |
| D | `_insert_filing` が `is_consolidated`, `document_type`, `submitted_at` をダミー値で保存 | `src/ingest/edinet_loader.py:188-205` |
| E | XBRL ZIP を PL/CF/BS で 3 回パースしており I/O/CPU が 3 倍 | `src/parser/edinet/xbrl_parser.py:26-148` |

---

## 3. 改修方針（このファイルだけで実装できるレベルの指示）

### 3.1 Downloader 層
1. **契約どおり単一銘柄を落とす**  
   - `EdinetDownloader.fetch_filings` に `sec_code: str` を必須引数として追加。  
   - クエリパラメータ `{'code': sec_code}` を追加し、docstring を「指定銘柄のみ」に更新。  
   - `runner.py` や CLI 呼び出し元ですべて `sec_code` を明示的に受け渡す。  
   - 複数銘柄対応が必要な場合は、リストを受け取ってループするヘルパー関数を別途用意する（契約破壊を避ける）。
2. **API キー検証をコンストラクタで実施**  
   - `__init__` に `api_key: str | None = None` を追加し、未指定時は `os.getenv` で取得。  
   - `if not api_key: raise ValueError("EDINET_API_KEY is required")` を実行して早期失敗。  
   - テスト容易性のため、API キーを依存として注入するシグネチャを `BaseDownloader` にも広げる。

### 3.2 Parser 層
1. **連結/単体の優先順位を設定化**  
   - `parser/edinet/utils.py` の `pick_current_value` に `preference: Literal["consolidated", "non_consolidated", "auto"]` を追加。  
   - 設定は `config/parser.py` などから注入し、`auto` は「単体があれば単体、なければ連結」にする。  
   - `docs/code_review.md` の該当指摘は「優先順位が固定」の問題として更新する。
2. **ZIP の再パースを解消**  
   - `FinancialSummary`, `CashFlowSummary`, `BalanceSheetSummary` を `BaseSummary` から派生させつつ、ZIP → `BeautifulSoup` 変換を一度だけ行う `XbrlZipCache` を新設 (`parser/edinet/xbrl_parser.py`).  
   - 既存クラスはキャッシュを受け取って XPath を変えるだけにし、`FinancialSummary.parse_zip` などから `with XbrlZipCache(zip_file) as cache:` を呼び出して 1 度で済ませる。

### 3.3 Ingest 層
1. **既存 doc_id の扱いを修正**  
   - `_get_existing_doc_ids` を `yield from cursor.fetchmany()` 方式にし、巨大セットを避ける。  
   - ループ側では「doc_id が存在し、かつ ZIP に更新タイムスタンプが新しい」場合のみ UPDATE 分岐に入るよう `process_zip` のロジックを変更。  
   - UPDATE 時は `filings` テーブルの `submitted_at` など全列を上書きできるようにする。
2. **edinet_code の UNKNOWN を禁止**  
   - `extract_basic_metadata_from_zip` で空文字／欠落時は例外を投げ、ログに ZIP 名を残してスキップ。  
   - もし EDINET が一部提出で code を欠落させる場合は、暫定 ID を `edinet_missing_<doc_id>` のようにユニーク化する。スキーマ変更は不要。
3. **Filing メタデータを DB に保存**  
   - `_insert_filing` の引数に `is_consolidated`, `document_type`, `submitted_at` を追加し、ZIP 内 `Submission/Type` や `ContextRef` から取得した実値を渡す。  
   - `filings` テーブルの `NOT NULL` 制約と整合するよう DDL を再確認し、必要なら migration を追加して `submitted_at TIMESTAMPTZ NOT NULL` 等に修正。

### 3.4 Query/Analytics 層（`docs/architecture.md` とのギャップ解消）
1. **Repository パターンの導入**  
   - `src/query/repositories/__init__.py`、`company.py`、`filing.py`、`statement.py` を新規作成し、既存の ad-hoc SQL 呼び出しを移動。  
   - `BaseRepository` を `db/core.py` の接続ヘルパーに依存注入させ、各 Repository は `list_for_company` などの明示的なメソッドを提供する。
2. **時系列 API の実装**  
   - `src/query/timeseries.py` を作成し、上で定義した Repository だけを使って EPS・売上などのヒストリーを返す `get_financial_history` を実装。  
   - ユニットテスト（`tests/unit/query/test_timeseries.py`）でフェイク Repository を使う。
3. **CLI/レポート連携**  
   - `scripts/show_company_report.py` を追加し、`CompanyReportGenerator`（`src/reports/generators/company.py`）を呼び出す。  
   - `ConsoleFormatter/CsvFormatter/MarkdownFormatter` を `src/reports/formatters/` 配下に用意し、Phase 2 のレポーティングに備える。

### 3.5 テスト整備
1. ルート直下に `tests/` ディレクトリを作成し、`pytest.ini` を用意。  
2. ダウンローダー、パーサー、ローダー、Repository、timeseries、report generator について happy/unhappy パスを埋める。  
3. `Makefile` に `test/unit` と `test/integration` ターゲットを追加し、README に利用方法を追記。

---

## 4. ドキュメント更新指針
1. `docs/code_review.md` では、上記 A〜E の再評価結果を反映した「第二版」を作成する。  
2. `docs/architecture.md` の Phase 1〜4 に、実装完了条件と Issue/PR テンプレートへのリンクを追記して進捗を見える化する。  
3. 本ドキュメントはレビュー会議のテンプレートとして保存し、各指摘の対応状況 (`TODO/DOING/DONE`) をチェックボックス化して利用する。

---

## 5. 実行順序（優先度付きバックログ）
1. Downloader 層の契約整備（単一銘柄 + API キー検証）
2. Ingest 層の doc_id, edinet_code, filing メタデータ修正
3. Parser 層の連結/単体設定化と ZIP キャッシュ導入
4. Repository + timeseries + CLI（`architecture.md` Phase 1-2）
5. テストスイートと Makefile タスク整備
6. ドキュメント（code_review.md, architecture.md）の第二版リリース

上記順序で着手すれば、ダウンロード～レポート出力までの主要バグを除去し、アーキテクチャ方針とコードベースを同期できる。
