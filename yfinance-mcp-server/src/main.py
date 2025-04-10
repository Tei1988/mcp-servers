#!/usr/bin/env python3
import asyncio
import logging
import os
import signal
import yfinance as yf
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any # 型ヒントのために追加

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

from mcp.types import ( # 必要な型定義をインポート
    Tool, TextContent,
    Resource, ResourceTemplate
)

# .envファイルから環境変数を読み込む (存在する場合)
load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Server インスタンスを作成
server = Server("yfinance-mcp-server")

# --- Tool Implementation ---
# 元の関数を実装部分として残す
async def get_stock_info_impl(args: dict) -> str:
    """yfinanceを使って株価情報を取得する (実装部分)"""
    ticker_symbol = args.get("ticker")
    if not ticker_symbol:
        raise McpError(ErrorCode.INVALID_PARAMS, "Ticker symbol ('ticker') is required.")

    period = args.get("period")
    start_date = args.get("start_date")
    end_date = args.get("end_date")
    interval = args.get("interval", "1d") # デフォルトは1日

    logger.debug(f"Fetching stock info for {ticker_symbol} (period={period}, start={start_date}, end={end_date}, interval={interval})")

    try:
        ticker = yf.Ticker(ticker_symbol)

        # period と start/end date の優先順位: start/end があればそちらを優先
        if start_date and end_date:
            # 日付文字列をdatetimeオブジェクトに変換 (エラーハンドリング追加)
            try:
                # yfinance は 文字列形式 'YYYY-MM-DD' を受け付ける
                # start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                # end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                history = ticker.history(start=start_date, end=end_date, interval=interval)
            except ValueError:
                raise McpError(ErrorCode.INVALID_PARAMS, "Invalid date format. Use YYYY-MM-DD.")
        elif period:
            history = ticker.history(period=period, interval=interval)
        else:
            # デフォルト期間 (例: 1ヶ月)
            history = ticker.history(period="1mo", interval=interval)

        if history.empty:
            # エラーではなく、空の結果を示すメッセージを返す
            return f"No data found for ticker {ticker_symbol} with the specified parameters."

        # Pandas DataFrameをJSON文字列に変換
        # 日付をISOフォーマットの文字列に変換しておく
        history.index = history.index.strftime('%Y-%m-%dT%H:%M:%S%z')
        history_json = history.to_json(orient="index", date_format="iso")

        return history_json

    except Exception as e:
        logger.exception(f"Error fetching data from yfinance for {ticker_symbol}: {e}")
        # yfinanceからの具体的なエラーメッセージを含めることも検討
        raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to fetch data for {ticker_symbol}: {str(e)}")


# --- MCP Handlers ---
@server.list_resources()
async def list_resources() -> list[Resource]:
    return []

@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    return []

@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツールをリストするハンドラ"""
    logger.debug("Handling ListTools request")
    # Tool オブジェクトではなく辞書形式で返す
    return [
        Tool(name = "get_stock_info",
             description = "指定された銘柄コードの株価履歴を取得します。",
             inputSchema = {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "証券コード (例: AAPL, 7203.T)",
                    },
                    "period": {
                        "type": "string",
                        "description": "取得期間 (例: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)",
                        "default": "1mo",
                    },
                    "interval": {
                        "type": "string",
                        "description": "データ間隔 (例: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)",
                        "default": "1d",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "開始日 (YYYY-MM-DD形式)。periodと同時に指定された場合は無視されます。",
                        "format": "date",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "終了日 (YYYY-MM-DD形式)。periodと同時に指定された場合は無視されます。",
                        "format": "date",
                    },
                },
                "required": ["ticker"],
            }
        ),
    ]

@server.call_tool()
async def call_tool(name, args: dict) -> dict: # 型ヒントを dict に修正
    """ツール呼び出しを処理するハンドラ"""
    logger.debug(f"Handling CallTool request for tool: {name}")

    if name == "get_stock_info":
        try:
            result_json = await get_stock_info_impl(args)
            # TextContent オブジェクトをインスタンス化して返す (type="text" を追加)
            return [
                TextContent(type="text", text=result_json) # type="text" を追加
            ]
            
        except McpError as e:
            logger.error(f"MCP Error calling tool {name}: {e.message} (Code: {e.code})")
            # エラーレスポンスでも TextContent を使用 (type="text" を追加)
            return [
                TextContent(type="text", text=f"Error: {e.message} (Code: {e.code})") # type="text" を追加
            ]
        except Exception as e:
            logger.exception(f"Unhandled error calling tool {name}: {e}")
            # エラーレスポンスでも TextContent を使用 (type="text" を追加)
            return [
                TextContent(type="text", text=f"Internal server error: {str(e)}") # type="text" を追加
            ]
    else:
        logger.warning(f"Tool '{name}' not found.")
        # エラーレスポンスでも TextContent を使用 (type="text" を追加)
        return [
            TextContent(type="text", text=f"Tool '{name}' not found.") # type="text" を追加
        ]
        # MCP仕様ではエラーコードも返せると良いが、ここでは省略
        # raise McpError(ErrorCode.METHOD_NOT_FOUND, f"Tool '{tool_name}' not found.")


async def main():
    """サーバーを起動し、終了シグナルを待つ"""
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)

if __name__ == "__main__":
    # main コルーチンを実行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.debug("Process interrupted by user.")
