"""
Flask アプリケーションの DeepL サービスのテストモジュール

python -m pytest app/tests/test_deepl_service.py -v
"""

import os
import unittest
from unittest.mock import Mock, patch

# app.mainをインポートする前に環境変数を設定
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key")

# Supabaseサービスをモックしてからapp.mainをインポート
with patch("app.context_processors.supabase_service") as mock_supabase:
    mock_supabase.get_data.return_value = [{"year": 2025}]
    from app.main import app


class DeepLServiceTestCase(unittest.TestCase):
    """DeepLサービスのテストケース"""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch("app.models.deepl_client.deepl.Translator")
    def test_deepl_translate_success(self, mock_translator):
        """DeepL 翻訳が正常に動作することをテストする"""
        from app.models.deepl_client import DeepLService

        # モックの設定
        mock_instance = Mock()
        mock_instance.translate_text.return_value = Mock(text="こんにちは")
        mock_translator.return_value = mock_instance

        with patch.dict(os.environ, {"DEEPL_API_KEY": "test_key"}):
            service = DeepLService()
            translated = service.translate("Hello", "JA")
            self.assertEqual(translated, "こんにちは")

    @patch("app.models.deepl_client.deepl.Translator")
    def test_deepl_translate_empty_text_returns_empty(self, mock_translator):
        """空文字列は空文字列を返すことを確認する"""
        from app.models.deepl_client import DeepLService

        mock_translator.return_value = Mock()
        with patch.dict(os.environ, {"DEEPL_API_KEY": "test_key"}):
            service = DeepLService()
            self.assertEqual(service.translate("", "JA"), "")

    def test_rate_limit_configuration(self):
        """translate メソッドにレートリミットデコレータが適用されているか確認"""
        from app.models.deepl_client import DeepLService

        with patch.dict(os.environ, {"DEEPL_API_KEY": "test_key"}):
            service = DeepLService()
            self.assertTrue(
                hasattr(service.translate, "__wrapped__"),
                "レートリミットデコレータが適用されていません",
            )
