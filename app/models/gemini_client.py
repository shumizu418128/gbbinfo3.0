import hashlib
import json
import os

from google import genai
from ratelimit import limits, sleep_and_retry

from app.config.config import (
    SAFETY_SETTINGS_BLOCK_ONLY_HIGH,
)
from app.config.logging_config import get_logger

logger = get_logger(__name__)


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

    # MARK: ask
    @sleep_and_retry
    @limits(calls=1, period=2)  # 2秒間に1回のコール制限
    def ask(self, prompt: str):
        """
        Gemini APIに同期で質問を送信し、レスポンスを取得する。

        Args:
            prompt (str): Gemini APIに送信するプロンプト文字列。

        Returns:
            dict: Gemini APIからのレスポンスを辞書形式で返す。エラー時は空の辞書を返す。

        Raises:
            ValueError: GEMINI_API_KEYが設定されていない場合に発生。
            Exception: Gemini API呼び出し時にその他の例外が発生した場合に発生。
        """

        # ここに書かないと循環インポートになる
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

            # 無期限キャッシュ（バックエンド実装差を避けるためtimeoutを明示）
            flask_cache.set(cache_key, response_dict, timeout=0)
            return response_dict

        except Exception as e:
            logger.error(f"[ask] GeminiService ask API call failed: {e}")
            # response_textとresponseが定義されている場合のみ出力
            try:
                logger.debug(f"[ask] Processed response: {response_text}")
                logger.debug(f"[ask] Original response: {response.text}")
                error_code = response_dict.get("error", {}).get("code")
                if error_code is not None:
                    return {"error_code": error_code}
            except NameError:
                logger.error("[ask] Error occurred before processing response")
            return {}


# グローバルインスタンス
gemini_service = GeminiService()
