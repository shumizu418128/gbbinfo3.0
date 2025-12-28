import hashlib
import os
import re

import deepl
from ratelimit import limits, sleep_and_retry

# レート制限設定
RATE_LIMIT_CALLS = 5
RATE_LIMIT_PERIOD = 1

# 絶対にBeatboxer名と被らないよう冗長なタグを使用
IGNORE_TAG = "_ignore_beatboxer_name_tag_"


class DeepLService:
    def __init__(self):
        api_key = os.environ.get("DEEPL_API_KEY")
        if not api_key:
            raise ValueError(
                "DEEPL_API_KEY環境変数が設定されていません。"
                "DeepL APIキーを設定してください。"
            )

        self.translator = deepl.Translator(api_key)

    def add_ignore_key(self, text: str, beatboxer_name: str) -> str:
        """
        特定のビートボクサー名を翻訳から除外するためのキーを追加する。

        Args:
            text (str): 入力テキスト。
            beatboxer_name (str): 除外したいビートボクサー名。

        Returns:
            str: ビートボクサー名が単語として現れる場合にのみタグで囲んだテキスト。

        Notes:
            - 名前が別の単語の一部になっている場合は置換しません。
            - 既にタグで囲まれている場合は二重に囲みません。
        """
        if not beatboxer_name:
            return text

        wrapped = f"<{IGNORE_TAG}>{beatboxer_name}</{IGNORE_TAG}>"
        # 既に囲まれている場合は処理不要
        if wrapped in text:
            return text

        # 単語境界でマッチするように negative/positive lookarounds を使用
        pattern = rf"(?<!\w){re.escape(beatboxer_name)}(?!\w)"

        return re.sub(pattern, wrapped, text, flags=re.IGNORECASE)

    def remove_ignore_key(self, text: str) -> str:
        """翻訳後のテキストから除外キーを削除する"""
        text = text.replace(f"<{IGNORE_TAG}>", "").replace(f"</{IGNORE_TAG}>", "")
        return text

    @sleep_and_retry
    @limits(calls=RATE_LIMIT_CALLS, period=RATE_LIMIT_PERIOD)
    def translate(
        self,
        text: str,
        target_lang: str,
        beatboxer_name: str,
    ) -> str:
        """
        DeepL APIを用いてテキストを翻訳します。

        Args:
            text (str): 翻訳対象のテキスト。
            target_lang (str): 翻訳先の言語コード。小文字でも可。
            beatboxer_name (str): ビートボクサー名。翻訳から除外されます。

        Returns:
            str: 翻訳後のテキスト。

        Notes:
            - レート制限: 1秒間に5回のリクエスト制限付き
            - 対応言語コード:
              * JA: 日本語
              * KO: 韓国語
              * EN-US, EN-GB: 英語（米国/英国）
              * その他多数の言語に対応
            - 空文字列や極端に短いテキストは翻訳されません

        Examples:
            >>> service = DeepLService()
            >>> result = service.translate("Hello", "JA")
            >>> print(result)
            'こんにちは'
        """
        target_lang_upper = target_lang.upper()

        # 空文字列チェック
        if not text or not text.strip():
            return ""

        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        question_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"deepl_translate_{target_lang_upper}_{question_hash}"

        # キャッシュから取得を試行 あるなら返す
        cached_data = flask_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        # ビートボクサー名を翻訳から除外
        text_with_ignore_key = self.add_ignore_key(text, beatboxer_name)

        result = self.translator.translate_text(
            text=text_with_ignore_key,
            source_lang="EN",
            target_lang=target_lang_upper,
            ignore_tags=[IGNORE_TAG],
            formality="prefer_more",
        )

        # 除外キーを削除
        text_ignore_key_removed = self.remove_ignore_key(result.text)

        # キャッシュに保存
        flask_cache.set(cache_key, text_ignore_key_removed)

        return text_ignore_key_removed


# グローバルインスタンス
deepl_service = DeepLService()
