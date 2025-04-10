# yfinance MCP Server Concept

## 概要

このドキュメントは、`yfinance` ライブラリを使用して株価などの金融データを取得するMCP (Model Context Protocol) サーバーのコンセプトを定義します。

## 目的

*   指定された銘柄の株価や関連情報を取得できるMCPサーバーを構築する。
*   クライアント（例: AIアシスタント）が容易に金融データへアクセスできるようにする。

## 機能要件

*   **データソース:** `yfinance` ライブラリを利用してデータを取得する。
*   **銘柄指定:** 証券コード（Ticker Symbol）または会社名で対象銘柄を指定できる。
    *   会社名からの証券コード検索機能が必要になる可能性があります。
*   **期間指定:** データ取得の対象期間（開始日、終了日）を指定できる。
*   **取得可能なデータ:**
    *   株価（始値、高値、安値、終値、出来高）
    *   企業情報（概要、セクター、業種など） - `yfinance` が提供する範囲で
    *   （将来的に）配当、株式分割などの情報

## 技術要素

*   **プログラミング言語:** Python 3.12 (`^3.12`)
*   **パッケージ管理・ビルドツール:** Poetry (`pyproject.toml` を使用)
*   **MCPサーバーフレームワーク:** mcp (`>=1.6.0,<2.0.0`)
*   **データ取得ライブラリ:** yfinance (`>=0.2.55,<0.3.0`), pandas (yfinanceの依存関係)
*   **環境変数管理:** python-dotenv (`>=1.1.0,<2.0.0`)
*   **通信技術:** 標準入出力 (StdioTransport)
*   **実行環境:** Docker (Alpine Linux ベースの軽量イメージ)

## 実装方針

1.  **プロジェクト初期化:** Poetry (または選択したツール) を使用してプロジェクトを初期化し、`pyproject.toml` を生成する。
2.  **依存関係の追加:** `poetry add` コマンドを使用して `pyproject.toml` に `mcp`, `yfinance`, `python-dotenv` を追加し、`poetry.lock` ファイルを生成・更新する。
3.  **MCPサーバー実装:** `mcp` ライブラリを使用してMCPサーバーの基本的な構造を `src/main.py` に作成する。
4.  **データ取得ロジック実装:** `src/main.py` 内に `yfinance` を利用したデータ取得関数 (`get_stock_info_impl`) を実装する。
    *   必須パラメータ: `ticker` (証券コード)
    *   オプションパラメータ: `period`, `interval`, `start_date`, `end_date`
    *   `start_date`/`end_date` が指定された場合は `period` より優先する。
    *   日付形式は `YYYY-MM-DD`。
    *   エラーハンドリング（無効なパラメータ、yfinanceからのエラー）。
5.  **MCPツール定義:** `src/main.py` の `@server.list_tools()` デコレータを使用して `get_stock_info` ツールを定義する。
    *   **ツール名:** `get_stock_info`
    *   **説明:** 指定された銘柄コードの株価履歴を取得します。
    *   **入力スキーマ:**
        *   `ticker` (string, required): 証券コード (例: AAPL, 7203.T)
        *   `period` (string, optional, default: "1mo"): 取得期間 (例: 1d, 5d, 1mo, ...)
        *   `interval` (string, optional, default: "1d"): データ間隔 (例: 1m, 1h, 1d, ...)
        *   `start_date` (string, optional, format: date): 開始日 (YYYY-MM-DD)
        *   `end_date` (string, optional, format: date): 終了日 (YYYY-MM-DD)
    *   **出力形式:** 株価履歴データを含むJSON文字列 (Pandas DataFrameを `to_json(orient="index", date_format="iso")` で変換したもの)。データが見つからない場合はその旨を示すメッセージ。エラー発生時はエラーメッセージ。
6.  **Docker化:**
    *   Alpine Linux ベースの軽量なマルチステージ `Dockerfile` を作成する。
    *   `docker buildx` を使用して、`linux/amd64` および `linux/arm64` プラットフォーム向けのイメージをビルドする。
    *   イメージ名は `tei1988/yfinance-mcp-server` とし、タグは `pyproject.toml` のバージョンを使用する (例: `0.1.0`)。
7.  **設定:** MCPクライアント (例: Cline) の設定ファイル (`cline_mcp_settings.json` など) に、ビルドした Docker イメージを使用するようにサーバー設定を登録する。
