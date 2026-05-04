# Scribe

音声文字起こしと要約を提供する統合サービス

## 概要

Scribe は音声ファイルの文字起こしとテキストの要約機能を提供する統合サービスです。以前は別々のサービスとして提供されていた transcriber と summarizer の機能を統合し、より使いやすく、保守性の高いパッケージとして再設計されています。

## 機能

- **音声文字起こし**: WAV 形式の音声ファイルをテキストに変換
- **テキスト要約**: 長いテキストを要約して短く簡潔にする
- **非同期処理**: バックグラウンドでの処理をサポート
- **ステータス管理**: 処理状況の追跡と管理
- **スケジュールタスク**: 定期的なメンテナンスタスクの実行

## 技術スタック

- **言語**: Python 3.12+
- **API フレームワーク**: FastAPI
- **非同期処理**: RQ (Redis Queue)
- **スケジューラー**: RQ Scheduler
- **データストア**: Redis
- **コンテナ化**: Docker

## アーキテクチャ

Scribe は以下のコンポーネントで構成されています：

1. **共通コンポーネント**
   - 共通データモデル
   - 抽象ジョブ処理クラス
   - ジョブ登録管理
   - Redis クライアント
   - ステータス管理

2. **機能モジュール**
   - 文字起こし機能
   - 要約機能

3. **サービス**
   - API サーバー
   - ワーカー
   - スケジューラー

## インストール

### 前提条件

- Python 3.12 以上
- uv
- Redis
- Docker と Docker Compose (オプション)

### ローカルインストール

```bash
# リポジトリのクローン
git clone https://github.com/t-ashula/scribe.git
cd scribe

# 依存関係のインストール
uv sync
```

### Docker を使用したインストール

```bash
# リポジトリのクローン
git clone https://github.com/t-ashula/scribe.git
cd scribe

# Docker Compose でサービスを起動
docker-compose up -d
```

## 使用方法

### API サーバー・ワーカー・スケジューラーの起動

Redis が起動済みであれば、以下のスクリプトで API / worker / scheduler をまとめて起動できます。

```bash
./scripts/dev-up.sh
```

必要に応じて以下の環境変数を上書きできます。

- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB`
- `GESHI_UPLOAD_DIR`
- `SCRIBE_HOST`
- `SCRIBE_PORT`

個別に起動したい場合は従来どおり次のコマンドを使えます。

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
uv run python -m src.worker
uv run python -m src.scheduler
```

## API エンドポイント

### 文字起こし

- `POST /transcribe`: 音声ファイルをアップロードして文字起こしジョブを登録
- `GET /transcribe/{request_id}`: 文字起こし結果の取得

### 要約

- `POST /summarize`: テキストを送信して要約ジョブを登録
- `GET /summarize/{request_id}`: 要約結果の取得

## 開発

### テストの実行

```bash
uv run pytest
```

### リンターの実行

```bash
# リンティングチェック
uv run ruff check .

# フォーマットチェック
uv run ruff format --check .

# フォーマット適用
uv run ruff format .
```

## ライセンス

[MIT License](../LICENSE)
