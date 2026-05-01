# コードレビュー（Object Design Style Guide / Fluent Python 観点）

## 所見

### 1. EDINETダウンローダーが責務どおりに銘柄を絞り込んでいない（重大）
- `src/downloader/edinet_downloader.py:25-48` のクラスは docstring で「単一銘柄の書類を取る」と宣言していますが、実装は `secCode` パラメータを持たず、APIクエリにも渡していないため、指定期間の全銘柄をダウンロードします。
- Object Design Style Guide が強調する「クラスの責務とインターフェースの一致」に反しており、利用者が意図せず大量のZIPを取得 / APIレートを消費する危険があります。
- `sec_code` などの依存を明示的に受け取り、メタデータおよび書類取得時にフィルタリングする構造へ改めると、クラス契約と実装が一致します。

### 2. APIキー未設定時に遅延失敗する（高）
- `src/downloader/edinet_downloader.py:28-58` では `self.api_key = os.getenv("EDINET_API_KEY")` をそのままリクエストに渡しており、未設定の場合はエラーが HTTP レイヤで初めて顕在化します。
- Fluent Python が推奨する「早く失敗し、明瞭なエラーを出す」原則を満たしておらず、原因切り分けが困難です。
- `__init__` でキー存在を検証し、欠落していれば `ValueError` などで即時に通知する、あるいは依存性注入でテスト可能な形にするべきです。

### 3. `_infer_fiscal_info` の四半期決定ロジックが誤り（高）
- `src/ingest/edinet_loader.py:101-124` は終了月を元に FY/Q1〜Q3 を決めていますが、12月決算を Q3 と誤分類し、6月決算などもFY扱いできません。
- Object Design Style Guide でいう「判断ロジックの隠れた知識」に該当し、誤った期間データが DB に永続化されます。
- EDINET の `docTypeCode` や報告期間長を参照して判定するか、少なくとも 12月=FY, 6/9/12月の四半期など実務に基づく分岐へ更新が必要です。

### 4. 既存 filing を丸ごとメモリに読み込んでいる（中）
- `src/ingest/edinet_loader.py:159-163` と `298-316` で `SELECT edinet_doc_id FROM filings` を全件取得して set に格納しています。
- filings が数万件を超えるとクライアント側RAMを圧迫し、テーブル全走査を毎回発生させます。Fluent Python でいう「ストリーミングやジェネレータを活かすべき箇所」でイagerロードになっています。
- 対応案として、処理対象ZIPの doc_id 一覧のみを `WHERE edinet_doc_id = ANY(...)` で問い合わせる、または `INSERT ... ON CONFLICT DO NOTHING` でDB側に存在チェックを委譲する等が考えられます。

### 5. XBRLの値取得が単体決算のみを優先し連結値を捨てている（中）
- `src/parser/edinet/utils.py:95-114` の `pick_current_value` は `NonConsolidatedMember` を含む context を優先し、それが無い場合のみ `CurrentYear` を拾います。
- 多くの有報は連結のみを開示するため、この優先順位では実質的に `None` が返り指標が欠落します。Object Design Style Guide の「実際のユースケースを代表するテストに合わせる」方針とも矛盾します。
- 連結値をデフォルトにし、単体を明示的に選べる設定を `edinet.yaml` に持たせるか、contextの Consolidated/NonConsolidated メンバーを判定して最適な値を返すよう改善が必要です。

### 6. テストスイートが存在しない（中）
- リポジトリ直下に `tests/` が存在せず、README に記載の `make test/unit` も未提供です。今回触れた不具合を検出する安全網がありません。
- Object Design Style Guide および Fluent Python の両書が推奨する「小さな協調クラス群＋テスト駆動」の実践から外れており、動作保証ができません。
- downloader / parser / ingest といった層ごとにユニットテスト、EDINET ZIP を使った統合テスト骨子を追加してください。

## 推奨アクション
1. `EdinetDownloader` に `sec_code`（もしくはクエリパラメータ）を追加し、責務を明確化する。
2. APIキーを必須依存として検証し、欠落時には CLI で即座に失敗させる。
3. `_infer_fiscal_info` を EDINET の docType/期間長に基づいて実装し、ユニットテストで和暦/暦年両方をカバーする。
4. 既存 filing の存在チェックを DB に委譲するか、ファイルバッチ単位の問い合わせに変え、ストリーミング処理へ寄せる。
5. `pick_current_value` / `pick_instant_value` に連結・単体の選択ポリシーを持たせ、設定で切り替え可能にする。
6. `tests/` ツリーを整備し、parser/dataloader/ingest それぞれの正常系・異常系を Pytest で自動化する。
