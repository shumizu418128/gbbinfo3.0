import hashlib
import json
import os
import re

from google import genai
from ratelimit import limits, sleep_and_retry

from app.config.config import (
    SAFETY_SETTINGS_BLOCK_ONLY_HIGH,
)

MODEL_NAME = "gemini-2.5-flash-lite"
RATE_LIMIT_PERIOD = 4


def _fix_json_brace_balance(text: str) -> str:
    """
    JSON文字列の括弧バランスを修正する。
    末尾の余分な閉じ括弧を削除する。

    Args:
        text (str): 修正対象のJSON文字列。

    Returns:
        str: 括弧バランスが修正されたJSON文字列。
    """
    # 中括弧のバランスをチェック
    open_braces = text.count("{")
    close_braces = text.count("}")
    if close_braces > open_braces:
        # 余分な閉じ括弧の数を計算
        excess = close_braces - open_braces
        # 末尾の連続する閉じ括弧から余分な分を削除
        # 末尾から走査して、連続する`}`のうち余分な分を削除
        stripped = text.rstrip()
        trailing_braces = len(stripped) - len(stripped.rstrip("}"))
        if trailing_braces > 0:
            # 末尾の連続する`}`のうち、余分な分だけ削除
            remove_count = min(excess, trailing_braces)
            if remove_count > 0:
                text = text[:-remove_count]

    # 角括弧のバランスをチェック
    open_brackets = text.count("[")
    close_brackets = text.count("]")
    if close_brackets > open_brackets:
        # 余分な閉じ角括弧の数を計算
        excess = close_brackets - open_brackets
        # 末尾の連続する閉じ角括弧から余分な分を削除
        stripped = text.rstrip()
        trailing_brackets = len(stripped) - len(stripped.rstrip("]"))
        if trailing_brackets > 0:
            # 末尾の連続する`]`のうち、余分な分だけ削除
            remove_count = min(excess, trailing_brackets)
            if remove_count > 0:
                text = text[:-remove_count]

    return text


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
    @limits(calls=1, period=RATE_LIMIT_PERIOD)  # 4秒間に1回のコール制限
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

        try:
            # メッセージを送信（同期版を使用）
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "safety_settings": SAFETY_SETTINGS_BLOCK_ONLY_HIGH,
                },
            )

            # まずクライアントがパース済みのオブジェクトを提供しているか確認
            response_dict = None
            parsed = getattr(response, "parsed", None)
            if parsed is not None:
                try:
                    # pydanticモデルやdictの場合に対応
                    if isinstance(parsed, dict):
                        response_dict = parsed
                    elif hasattr(parsed, "dict"):
                        response_dict = parsed.dict()
                    else:
                        response_dict = parsed
                except Exception:
                    response_dict = None

            # parsedが使えない場合はtextを解析する
            if response_dict is None:
                response_text = getattr(response, "text", "") or ""
                # 不要な外部URLや前後空白を削除
                response_text = response_text.replace(
                    "https://gbbinfo-jpn.onrender.com", ""
                ).strip()

                # 括弧バランスを修正
                response_text = _fix_json_brace_balance(response_text)

                # 直接JSONを試す
                try:
                    response_dict = json.loads(response_text)
                except json.JSONDecodeError:
                    # 中括弧または角括弧で包まれた最初のJSON部分を抽出して試す
                    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response_text)
                    if m:
                        candidate = m.group(1)
                        # 括弧バランスを修正
                        candidate = _fix_json_brace_balance(candidate)
                        try:
                            response_dict = json.loads(candidate)
                        except json.JSONDecodeError as e:
                            # JSONパースに失敗した場合はログを出力してNoneを返す
                            print(
                                f"GeminiService: JSONパースに失敗しました。候補文字列: {candidate[:500]}",
                                flush=True,
                            )
                            print(f"JSONDecodeError: {e}", flush=True)
                            response_dict = None
                    else:
                        # キー:値ペアのみが返るケースを想定して、中括弧でラップして試す
                        if re.search(r"\"?\w+\"?\s*:\s*\"?[^,}]+\"?", response_text):
                            candidate = "{" + response_text + "}"
                            # 括弧バランスを修正
                            candidate = _fix_json_brace_balance(candidate)
                            try:
                                response_dict = json.loads(candidate)
                            except json.JSONDecodeError as e:
                                # JSONパースに失敗した場合はログを出力してNoneを返す
                                print(
                                    f"GeminiService: JSONパースに失敗しました。候補文字列: {candidate[:500]}",
                                    flush=True,
                                )
                                print(f"JSONDecodeError: {e}", flush=True)
                                response_dict = None

            # リスト形式の場合は最初の要素を取得
            if isinstance(response_dict, list) and len(response_dict) > 0:
                response_dict = response_dict[0]

            if response_dict is None:
                raise ValueError("Could not parse Gemini response as JSON")

            flask_cache.set(cache_key, response_dict)
            return response_dict

        except Exception as e:
            print(f"GeminiService ask API呼び出し失敗: {e}", flush=True)
            # response_textとresponseが定義されている場合のみ出力（先頭を制限してログ出力）
            try:
                rt = locals().get("response_text", None)
                if rt is not None:
                    print(
                        f"処理済みレスポンス（先頭2000文字）: {rt[:2000]}", flush=True
                    )
                original_text = getattr(response, "text", None)
                if original_text is not None:
                    print(
                        f"元のレスポンス（先頭2000文字）: {original_text[:2000]}",
                        flush=True,
                    )
                return {}
            except NameError:
                print("レスポンスの処理前にエラーが発生しました", flush=True)
            return {}


# グローバルインスタンス
gemini_service = GeminiService()
