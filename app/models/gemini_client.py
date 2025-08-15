import asyncio
import hashlib
import json
import os

from asyncio_throttle import Throttler
from google import genai

from app.models.config.gemini_config import (
    SAFETY_SETTINGS_BLOCK_ONLY_HIGH,
)

# 2秒間隔で1回のリクエストを許可
limiter = Throttler(rate_limit=1, period=2)


class GeminiService:
    """
    Gemini APIに質問を送信するクライアントクラス。

    Attributes:
        client: Gemini APIのクライアントインスタンス
        limiter: レートリミッター
        SAFETY_SETTINGS: セーフティ設定
    """

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません")
        self._client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            self._client = genai.Client(api_key=api_key)
        return self._client

    async def ask(self, prompt: str):
        """
        Gemini APIに質問を送信するメソッド。
        グローバルなレート制限で2秒間隔を保証します。

        Args:
            prompt (str): ユーザーからの質問。

        Returns:
            dict: Gemini APIからのレスポンスを辞書形式で返す
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        # キャッシュキーを生成
        cache_key = "gemini_search_" + hashlib.md5(prompt.encode("utf-8")).hexdigest()

        # キャッシュから取得を試行 あるなら返す
        cached_data = flask_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        async with limiter:
            try:
                # メッセージを送信
                response = await self.client.aio.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "safety_settings": SAFETY_SETTINGS_BLOCK_ONLY_HIGH,
                    },
                )

                # レスポンスをダブルクォーテーションに置き換え
                response_text = response.text.replace("'", '"').replace(
                    "https://gbbinfo-jpn.onrender.com", ""
                )

                # レスポンスをJSONに変換
                response_dict = json.loads(response_text)

                # リスト形式の場合は最初の要素を取得
                if isinstance(response_dict, list) and len(response_dict) > 0:
                    response_dict = response_dict[0]

                flask_cache.set(cache_key, response_dict)
                return response_dict

            except Exception as e:
                print(f"GeminiService ask API呼び出し失敗: {e}", flush=True)
                print(f"処理済みレスポンス: {response_text}", flush=True)
                print(f"元のレスポンス: {response.text}", flush=True)
                return {}

    def ask_sync(self, prompt: str):
        return asyncio.run(self.ask(prompt))


# グローバルインスタンス
gemini_service = GeminiService()
