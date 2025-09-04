import asyncio
import hashlib
import json
import os
from asyncio_throttle import Throttler

from google import genai
from ratelimit import limits, sleep_and_retry

from app.config.config import (
    SAFETY_SETTINGS_BLOCK_ONLY_HIGH,
)


class GeminiService:
    """
    Gemini APIに質問を送信するクライアントクラス。

    Attributes:
        client: Gemini APIのクライアントインスタンス
        throttler: レートリミッター
        SAFETY_SETTINGS: セーフティ設定
    """

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません")
        self._client = None
        self._throttler = Throttler(rate_limit=1, period=2)  # 2秒間に1回

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            self._client = genai.Client(api_key=api_key)
        return self._client

    # MARK: ask (async version)
    async def ask(self, prompt: str):
        """
        Gemini APIに非同期で質問を送信し、レスポンスを取得する。

        Args:
            prompt (str): Gemini APIに送信するプロンプト文字列。

        Returns:
            dict: Gemini APIからのレスポンスを辞書形式で返す。エラー時は空の辞書を返す。

        Raises:
            ValueError: GEMINI_API_KEYが設定されていない場合に発生。
            Exception: Gemini API呼び出し時にその他の例外が発生した場合に発生。
        """
        async with self._throttler:
            # ここに書かないと循環インポートになる
            from app.cache import sanic_cache

            # キャッシュキーを生成
            cache_key = "gemini_search_" + hashlib.md5(prompt.encode("utf-8")).hexdigest()

            # キャッシュから取得を試行 あるなら返す
            cached_data = await sanic_cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # あとの置き換えでエラーになるので、シングルクォーテーションを削除
            prompt = prompt.replace("'", " ")

            try:
                # メッセージを送信（同期版を使用、将来的にAsync版が利用可能になったら変更）
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model="gemini-2.0-flash-lite",
                        contents=prompt,
                        config={
                            "response_mime_type": "application/json",
                            "safety_settings": SAFETY_SETTINGS_BLOCK_ONLY_HIGH,
                        },
                    )
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

                await sanic_cache.set(cache_key, response_dict)
                return response_dict

            except Exception as e:
                print(f"GeminiService ask API呼び出し失敗: {e}", flush=True)
                # response_textとresponseが定義されている場合のみ出力
                try:
                    print(f"処理済みレスポンス: {response_text}", flush=True)
                    print(f"元のレスポンス: {response.text}", flush=True)
                except NameError:
                    print("レスポンスの処理前にエラーが発生しました", flush=True)
                return {}

    # MARK: ask sync (backward compatibility)
    @sleep_and_retry
    @limits(calls=1, period=2)  # 2秒間に1回のコール制限
    def ask_sync(self, prompt: str):
        """同期版の互換性メソッド。新しいコードではask()を使用してください。"""
        # 同期版を残しておく（後方互換性のため）
        from app.main import flask_cache

        # キャッシュキーを生成
        cache_key = "gemini_search_" + hashlib.md5(prompt.encode("utf-8")).hexdigest()

        # キャッシュから取得を試行 あるなら返す
        cached_data = flask_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        # あとの置き換えでエラーになるので、シングルクォーテーションを削除
        prompt = prompt.replace("'", " ")

        try:
            # メッセージを送信（同期版を使用）
            response = self.client.models.generate_content(
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
            print(f"GeminiService ask_sync API呼び出し失敗: {e}", flush=True)
            return {}


# グローバルインスタンス
gemini_service = GeminiService()
