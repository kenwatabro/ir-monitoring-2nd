# IR Monitoring 2nd

EDINET APIを使用して財務情報をダウンロード・解析するプロジェクトです。

## 必要な環境

このプロジェクトを実行するには、以下のソフトウェアが必要です：

- Docker Desktop（PostgreSQLサーバーをコンテナとして実行）
- PostgreSQL クライアント（psql）（データベース操作・DDL実行用）
- Python 3.x と仮想環境

### 1. Docker Desktop のインストール

#### macOS

```bash
brew install --cask docker
```

インストール後、Docker Desktopを起動：

```bash
open -a Docker
```

#### Linux

Docker Engineをインストール：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# または、公式のDocker Engineをインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

**重要：Docker権限の設定（SSH接続先のUbuntu環境など）**

Dockerコマンドを`sudo`なしで実行するには、ユーザーを`docker`グループに追加する必要があります：

```bash
# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# グループの変更を反映するため、一度ログアウトして再ログインするか、
# 以下のコマンドで新しいグループ設定を適用
newgrp docker

# 動作確認
docker version
```

**注意：** グループの変更を反映するには、SSH接続を一度切断して再接続するか、`newgrp docker`コマンドを実行してください。

一時的に`sudo`を使用する場合：

```bash
sudo docker run --name ir-monitoring-postgres \
  -e POSTGRES_USER=ir_user \
  -e POSTGRES_PASSWORD=ir_password \
  -e POSTGRES_DB=ir_monitoring \
  -p 5432:5432 \
  -d postgres:15
```

Docker Desktopを使用する場合：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker-desktop
```

#### Windows

1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) をダウンロード
2. インストーラーを実行してインストール
3. Docker Desktopを起動

**動作確認（全OS共通）：**

```bash
docker version
```

### 2. PostgreSQL クライアント（psql）のインストール

#### macOS

```bash
brew install postgresql@15
```

PATHに追加（一時的）：

```bash
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
```

永続的に使用する場合（`~/.zshrc`に追加）：

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y postgresql-client

# CentOS/RHEL/Fedora
sudo yum install -y postgresql15
# または
sudo dnf install -y postgresql15
```

#### Windows

1. [PostgreSQL for Windows](https://www.postgresql.org/download/windows/) をダウンロード
2. インストーラーを実行（psqlのみが必要な場合は「Command Line Tools」を選択）
3. または、[Chocolatey](https://chocolatey.org/)を使用：

```powershell
choco install postgresql15 --params '/Password:your_password'
```

**動作確認（全OS共通）：**

```bash
psql --version
```

### 3. Python 3.x と仮想環境

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Windows

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## セットアップ手順

### 1. PostgreSQLサーバーの起動

```bash
docker run --name ir-monitoring-postgres \
  -e POSTGRES_USER=ir_user \
  -e POSTGRES_PASSWORD=ir_password \
  -e POSTGRES_DB=ir_monitoring \
  -p 5432:5432 \
  -d postgres:15
```

### 2. DDLの実行

```bash
docker exec -i ir-monitoring-postgres psql -U ir_user -d ir_monitoring < ddl/001_core_financial_reporting.sql
docker exec -i ir-monitoring-postgres psql -U ir_user -d ir_monitoring < ddl/002_edinet_scanned_dates.sql
docker exec -i ir-monitoring-postgres psql -U ir_user -d ir_monitoring < ddl/003_add_unique_constraints.sql
```

### 3. 環境変数の設定

`.env`ファイルを作成し、EDINET APIキーを設定：

```bash
cp .env.example .env
# .envファイルを編集してEDINET_API_KEYを設定
```

### 4. データのダウンロード

日常運用は `scripts/ops/bulk_download_edinet.py` を使用：

```bash
source venv/bin/activate

# 2015年から今日まで全件取得（バックグラウンド推奨）
python scripts/ops/bulk_download_edinet.py --start 2015-01-01 &

# 特定期間のみ
python scripts/ops/bulk_download_edinet.py --start 2024-01-01 --end 2024-01-31
```

> **簡易CLI（互換用）:** `python -m src.download <start_date> <end_date>` でも動作しますが、
> スキャン済み日付のスキップなど運用機能が省略されています。

## データベース接続

デフォルトの接続情報：

- ホスト: `localhost`
- ポート: `5432`
- データベース名: `ir_monitoring`
- ユーザー名: `ir_user`
- パスワード: `ir_password`

環境変数`PGURL`を設定することで、接続文字列を指定できます：

#### macOS / Linux

```bash
export PGURL="postgresql://ir_user:ir_password@localhost:5432/ir_monitoring"
```

#### Windows

```powershell
$env:PGURL="postgresql://ir_user:ir_password@localhost:5432/ir_monitoring"
```

## 便利なコマンド

### データベースに接続

```bash
docker exec -it ir-monitoring-postgres psql -U ir_user -d ir_monitoring
```

### テーブル一覧の確認

```bash
docker exec ir-monitoring-postgres psql -U ir_user -d ir_monitoring -c "\dt"
```

### コンテナの停止・削除

```bash
# コンテナを停止
docker stop ir-monitoring-postgres

# コンテナを削除
docker rm ir-monitoring-postgres

# データも含めて完全に削除する場合
docker rm -v ir-monitoring-postgres
```

## CLI コマンド一覧

このプロジェクトでは、財務データの取得・分析・レポート生成のための各種CLIコマンドを提供しています。

### 前提条件

```bash
# 仮想環境の有効化
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate      # Windows

# 環境変数の設定
export PGURL="postgresql://ir_user:ir_password@localhost:5432/ir_monitoring"
```

---

### 1. データダウンロード＆ロード（EDINET API）

ダウンロードとDBロードをまとめて行います（推奨）：

```bash
python scripts/ops/bulk_download_edinet.py --start <開始日> [--end <終了日>]
```

**主なオプション:**
| オプション | 説明 | デフォルト |
|------------|------|-----------|
| `--start` | ダウンロード開始日（YYYY-MM-DD） | 必須 |
| `--end` | ダウンロード終了日（YYYY-MM-DD） | 今日 |
| `--download-only` | ダウンロードのみ（DBロードなし） | - |
| `--load-only` | DBロードのみ（既存ZIPを対象） | - |

**使用例:**

```bash
# 2024年12月のデータをダウンロード＆ロード
python scripts/ops/bulk_download_edinet.py --start 2024-12-01 --end 2024-12-31

# 全期間を一括取得（バックグラウンド）
python scripts/ops/bulk_download_edinet.py --start 2015-01-01 &
```

---

### 2. データベースへのロード（ZIPが既にある場合）

ダウンロード済みZIPを解析してデータベースに格納します。

```bash
python scripts/ops/load_edinet_to_db.py [オプション]
```

**オプション:**
| オプション | 説明 | デフォルト |
|------------|------|-----------|
| `--max-files` | 処理するファイル数の上限 | 全件 |

**使用例:**

```bash
# 全ファイルをロード
python scripts/ops/load_edinet_to_db.py

# 最初の20件のみロード（テスト用）
python scripts/ops/load_edinet_to_db.py --max-files 20
```

---

### 3. 銘柄レポート生成

指定銘柄の財務推移レポートを生成します。

```bash
python scripts/ops/show_company_report.py [銘柄コード] [オプション]
```

**引数:**
| 引数 | 説明 | 例 |
|------|------|-----|
| `銘柄コード` | 証券コード（4桁） | `7203` |

**オプション:**
| オプション | 説明 | デフォルト |
|------------|------|-----------|
| `--edinet` | EDINETコードで指定 | - |
| `--format` | 出力形式（console/csv/markdown） | `console` |
| `--years` | 取得する年数 | `5` |

**使用例:**

```bash
# 証券コードで検索してコンソール出力
python scripts/ops/show_company_report.py 7203

# EDINETコードで検索
python scripts/ops/show_company_report.py --edinet E02275-000

# Markdown形式で出力
python scripts/ops/show_company_report.py 7203 --format markdown

# CSV形式で10年分を出力
python scripts/ops/show_company_report.py 7203 --format csv --years 10

# 古いデータがある場合は年数を増やす
python scripts/ops/show_company_report.py --edinet E02275-000 --years 10
```

**出力例（console）:**

```
=== トヨタ自動車株式会社 財務推移 ===

決算期                    売上高            営業利益            経常利益             純利益        EPS
-------------------------------------------------------------------------------------
2020 FY          29,929,992         2,442,869         2,792,942         2,076,183     146.98
2021 FY          27,214,594         1,320,888         2,324,763         2,282,378     161.59
2022 FY          31,379,507         2,995,697         3,990,532         2,850,110     202.22
2023 FY          37,154,298         2,725,025         3,668,733         2,451,318     178.42
2024 FY          45,095,325         5,352,934         6,070,093         4,944,933     365.41

※ 金額は百万円単位
```

---

### 4. スクリーナー実行

設定した条件で銘柄をスクリーニングします。`--ticker` は必須です。

```bash
python scripts/ops/run_screener.py [オプション]
```

**オプション:**
| オプション | 説明 | デフォルト |
|------------|------|-----------|
| `--list` | 利用可能なスクリーナーを表示 | - |
| `--name` | 実行するスクリーナー名 | - |
| `--ticker` | 評価する証券コード（必須） | - |
| `--years` | 分析対象年数 | `5` |
| `--min-growth` | 最低成長率（eps_growth, revenue_growth用） | `0.15` |
| `--min-margin` | 最低利益率（profit_margin用） | `0.10` |
| `--json` | 結果をJSON形式で出力 | - |

**利用可能なスクリーナー:**
| 名前 | 説明 |
|------|------|
| `eps_growth` | 過去3年のEPS成長率が15%以上 |
| `revenue_growth` | 過去3年の売上高成長率が10%以上 |
| `profit_margin` | 営業利益率が10%以上 |

**使用例:**

```bash
# 利用可能なスクリーナーを表示
python scripts/ops/run_screener.py --list

# EPS成長スクリーナーを実行
python scripts/ops/run_screener.py --name eps_growth --ticker 7203

# 売上成長率20%以上でスクリーニング
python scripts/ops/run_screener.py --name revenue_growth --ticker 7203 --min-growth 0.20

# 営業利益率15%以上でスクリーニング
python scripts/ops/run_screener.py --name profit_margin --ticker 7203 --min-margin 0.15

# 結果をJSON形式で出力
python scripts/ops/run_screener.py --name eps_growth --ticker 7203 --json
```

**出力例:**

```
利用可能なスクリーナー:
  eps_growth: 過去3年のEPS成長率が15%以上
  profit_margin: 営業利益率が10%以上
  revenue_growth: 過去3年の売上高成長率が10%以上
```

---

### クイックスタート例

```bash
# 1. 仮想環境の有効化と環境変数設定
source venv/bin/activate
export PGURL="postgresql://ir_user:ir_password@localhost:5432/ir_monitoring"

# 2. 直近1週間のデータをダウンロード
python -m src.download 2024-12-20 2024-12-27 --output-dir data/raw/edinet

# 3. ロードのみ試す場合（最初は20件でテスト）
python scripts/ops/load_edinet_to_db.py --max-files 20

# 4. 銘柄のレポートを確認
python scripts/ops/show_company_report.py --edinet E02275-000 --years 10

# 5. スクリーナーで銘柄評価
python scripts/ops/run_screener.py --name profit_margin --ticker 7203 --min-margin 0.15
```

---

## プロジェクト構造

```
ir-monitoring-2nd/
├── src/
│   ├── downloader/        # データダウンロード（EDINET等）
│   │   ├── edinet/        # EDINETダウンローダー
│   │   └── factory.py     # ダウンローダーファクトリ
│   ├── parser/            # XBRLパーサー
│   │   └── factory.py     # パーサーファクトリ
│   ├── ingest/            # データベース格納
│   │   ├── edinet/        # EDINETローダー
│   │   └── factory.py     # ローダーファクトリ
│   ├── query/             # データ取得・リポジトリ
│   │   ├── repositories/  # Company/Filing/Statement リポジトリ
│   │   └── timeseries.py  # 時系列データ取得
│   ├── reports/           # レポート生成
│   │   ├── formatters/    # Console/CSV/Markdown フォーマッター
│   │   └── generators/    # レポートジェネレーター
│   └── analytics/         # 分析・スクリーニング
│       ├── registry.py    # スクリーナーレジストリ
│       └── screeners/     # 各種スクリーナー
├── scripts/
│   ├── ops/               # 日常運用スクリプト
│   └── maintenance/       # メンテナンス用スクリプト
│       └── oneoff/        # 一回限りの修正スクリプト
├── ddl/                   # データベーススキーマ定義
├── data/raw/              # ダウンロードした生データ
└── tests/                 # テストコード
```

詳細は`AGENTS.md`および`docs/architecture.md`を参照してください。

