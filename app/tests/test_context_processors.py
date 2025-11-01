"""
Flask アプリケーションのコンテキストプロセッサのテストモジュール

python -m pytest app/tests/test_context_processors.py -v
"""

import json
import os
import time
import unittest
from unittest.mock import Mock, patch

from app.context_processors import (
    get_available_years,
    is_early_access,
    is_latest_year,
    is_translated,
)
from app.main import app

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


class ContextProcessorsTestCase(unittest.TestCase):
    """
    コンテキストプロセッサのテストケース
    """

    def setUp(self):
        """テストの前準備"""
        app.config["TESTING"] = True
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()

    @patch("app.context_processors.supabase_service")
    def test_get_available_years(self, mock_supabase):
        """利用可能な年度の取得テスト"""
        # キャッシュをクリア
        from app.main import flask_cache

        flask_cache.delete("available_years")

        # モックデータの設定
        mock_supabase.get_data.return_value = [
            {"year": 2025},
            {"year": 2024},
            {"year": 2023},
        ]

        result = get_available_years()

        # 降順でソートされていることを確認（実際の期待値は[2025, 2024, 2023]）
        self.assertEqual(result, [2025, 2024, 2023])

        # Supabaseが正しいパラメータで呼ばれていることを確認
        mock_supabase.get_data.assert_called_once()

    def test_is_latest_year(self):
        """最新年度判定のテスト"""
        with patch("app.context_processors.get_available_years") as mock_get_years:
            with patch("app.context_processors.datetime") as mock_datetime:
                mock_get_years.return_value = [2025, 2024, 2023]
                mock_datetime.now.return_value.year = 2025

                # 現在年度は最新年度
                self.assertTrue(is_latest_year(2025))

                # 過去年度は最新年度ではない
                self.assertFalse(is_latest_year(2024))

    def test_is_early_access(self):
        """早期アクセス判定のテスト"""
        with patch("app.context_processors.datetime") as mock_datetime:
            mock_datetime.now.return_value.year = 2025

            # 未来年度は早期アクセス
            self.assertTrue(is_early_access(2026))

            # 現在年度は早期アクセスではない
            self.assertFalse(is_early_access(2025))

            # 過去年度は早期アクセスではない
            self.assertFalse(is_early_access(2024))

    def test_is_translated(self):
        """翻訳判定のテスト"""
        # 日本語は常にTrue
        self.assertTrue(is_translated("/test", "ja", set()))

        # 英語は翻訳ファイルに依存
        translated_urls = {"/test"}
        self.assertTrue(is_translated("/test", "en", translated_urls))
        self.assertFalse(is_translated("/not-translated", "en", translated_urls))
