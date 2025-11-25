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
```

### 3. 環境変数の設定

`.env`ファイルを作成し、EDINET APIキーを設定：

```bash
cp env.example .env
# .envファイルを編集してEDINET_API_KEYを設定
```

### 4. データのダウンロード

#### macOS / Linux

```bash
source venv/bin/activate
python -m src.download <start_date> <end_date> --database-url postgresql://ir_user:ir_password@localhost:5432/ir_monitoring
```

例：

```bash
python -m src.download 2024-01-01 2024-01-31 --database-url postgresql://ir_user:ir_password@localhost:5432/ir_monitoring
```

#### Windows

```powershell
venv\Scripts\activate
python -m src.download <start_date> <end_date> --database-url postgresql://ir_user:ir_password@localhost:5432/ir_monitoring
```

例：

```powershell
python -m src.download 2024-01-01 2024-01-31 --database-url postgresql://ir_user:ir_password@localhost:5432/ir_monitoring
```

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

## プロジェクト構造

- `src/` - Pythonソースコード
- `ddl/` - データベーススキーマ定義（DDL）
- `scripts/` - 自動化スクリプト
- `data/raw/` - ダウンロードした生データ（.gitignoreに含まれる）

詳細は`AGENTS.md`を参照してください。

