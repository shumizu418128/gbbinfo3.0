import asyncio

from googletrans import Translator
from ratelimit import limits, sleep_and_retry


class GoogletransService:
    """
    Google Translate API (googletrans) を用いてテキストを翻訳するクライアントクラス。

    Attributes:
        client: googletransのTranslatorインスタンス
    """
    async def async_translate(self, text: str, src: str, dest: str):
        """
        Google Translate API (googletrans) を用いてテキストを翻訳します。

        Args:
            text (str): 翻訳対象のテキスト。
            src (str): 翻訳元の言語コード（例: 'en', 'ja'）。
            dest (str): 翻訳先の言語コード（例: 'en', 'ja'）。

        Returns:
            str: 翻訳後のテキスト。

        Notes:
            - googletransライブラリを使用して翻訳します。
            - 1秒間に1回のコール制限付きです（API制限対策）。
        """
        translator = Translator()
        response = await translator.translate(text, src=src, dest=dest)
        return response.text

    @sleep_and_retry
    @limits(calls=1, period=1)  # 1秒間に1回のコール制限
    def translate(self, text: str, src: str, dest: str):
        return asyncio.run(self.async_translate(text, src, dest))


# グローバルインスタンス
googletrans_service = GoogletransService()
