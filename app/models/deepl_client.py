import hashlib
import os

import deepl
from ratelimit import limits, sleep_and_retry

# レート制限設定
RATE_LIMIT_CALLS = 5
RATE_LIMIT_PERIOD = 1

# DeepL APIのコンテキストとカスタム指示 英語推奨
CONTEXT = "This text is intended to provide information about Beatboxers {name} participating in the GBB (Grand Beatbox Battle)."
CUSTOM_INSTRUCTIONS = (
    "Do not translate the name ({name}); leave it as is in the original."
)


class DeepLService:
    def __init__(self):
        api_key = os.environ.get("DEEPL_API_KEY")
        if not api_key:
            raise ValueError(
                "DEEPL_API_KEY環境変数が設定されていません。"
                "DeepL APIキーを設定してください。"
            )
        self.translator = deepl.Translator(api_key)

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

        result = self.translator.translate_text(
            text=text,
            source_lang="EN",
            target_lang=target_lang_upper,
            formality="prefer_more",
            context=CONTEXT.format(name=beatboxer_name),
            custom_instructions=CUSTOM_INSTRUCTIONS.format(name=beatboxer_name),
        )

        # キャッシュに保存
        flask_cache.set(cache_key, result.text)

        return result.text


# グローバルインスタンス
deepl_service = DeepLService()
