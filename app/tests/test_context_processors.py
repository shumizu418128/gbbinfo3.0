"""
Flask アプリケーションのコンテキストプロセッサのテストモジュール

python -m pytest app/tests/test_context_processors.py -v
"""

import unittest
from unittest.mock import MagicMock, patch

# Supabaseサービスをモックしてからapp.mainをインポート
with patch("app.context_processors.supabase_service") as mock_supabase:
    mock_supabase.get_data.return_value = [{"year": 2025}]
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

    @patch("app.context_processors.BASE_DIR")
    def test_get_others_content(self, mock_base_dir):
        """'Others'カテゴリのコンテンツ取得テスト"""
        from pathlib import Path

        from app.context_processors import get_others_content

        # モックのPathオブジェクトを作成
        mock_path = MagicMock(spec=Path)
        mock_base_dir.__truediv__ = MagicMock(return_value=mock_path)

        # globの結果をモック（stemで.htmlを除いたファイル名を返す）
        mock_file1 = MagicMock()
        mock_file1.stem = "about"
        mock_file2 = MagicMock()
        mock_file2.stem = "contact"
        mock_file3 = MagicMock()
        mock_file3.stem = "faq"

        mock_base_dir.glob.return_value = [mock_file1, mock_file2, mock_file3]

        result = get_others_content()

        # 結果の確認
        self.assertEqual(result, ["about", "contact", "faq"])
        mock_base_dir.glob.assert_called_once_with("app/templates/others/*.html")

    @patch("app.context_processors.BASE_DIR")
    def test_get_travel_content(self, mock_base_dir):
        """'Travel'カテゴリのコンテンツ取得テスト"""
        from pathlib import Path

        from app.context_processors import get_travel_content

        # モックのPathオブジェクトを作成
        mock_path = MagicMock(spec=Path)
        mock_base_dir.__truediv__ = MagicMock(return_value=mock_path)

        # globの結果をモック
        mock_file1 = MagicMock()
        mock_file1.stem = "hotel"
        mock_file2 = MagicMock()
        mock_file2.stem = "transportation"

        mock_base_dir.glob.return_value = [mock_file1, mock_file2]

        result = get_travel_content()

        # 結果の確認
        self.assertEqual(result, ["hotel", "transportation"])
        mock_base_dir.glob.assert_called_once_with("app/templates/travel/*.html")

    @patch("app.context_processors.BASE_DIR")
    def test_get_yearly_content(self, mock_base_dir):
        """年度別コンテンツ取得テスト"""
        from pathlib import Path

        from app.context_processors import get_yearly_content

        # モックのPathオブジェクトを作成
        mock_path = MagicMock(spec=Path)
        mock_base_dir.__truediv__ = MagicMock(return_value=mock_path)

        # 2024年のファイル
        mock_file_2024_1 = MagicMock()
        mock_file_2024_1.stem = "top"
        mock_file_2024_2 = MagicMock()
        mock_file_2024_2.stem = "rule"

        # 2023年のファイル
        mock_file_2023_1 = MagicMock()
        mock_file_2023_1.stem = "top"

        # globの呼び出しごとに異なる結果を返す
        def glob_side_effect(pattern):
            if "2024" in pattern:
                return [mock_file_2024_1, mock_file_2024_2]
            elif "2023" in pattern:
                return [mock_file_2023_1]
            return []

        mock_base_dir.glob.side_effect = glob_side_effect

        available_years = [2024, 2023]
        years_list, contents_per_year = get_yearly_content(available_years)

        # 結果の確認
        self.assertEqual(years_list, [2024, 2024, 2023])
        self.assertEqual(contents_per_year, ["top", "rule", "top"])

    @patch("app.main.flask_cache")
    @patch("app.context_processors.supabase_service")
    def test_get_participant_id(self, mock_supabase, mock_flask_cache):
        """参加者ID取得テスト"""
        from app.context_processors import get_participant_id

        # キャッシュをクリア
        mock_flask_cache.delete("participant_id_mode_list")

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            # Participantテーブルのデータ
            [
                {
                    "id": 1,
                    "name": "Solo Player",
                    "Category": {"is_team": False},
                },
                {
                    "id": 2,
                    "name": "Team A",
                    "Category": {"is_team": True},
                },
            ],
            # ParticipantMemberテーブルのデータ
            [
                {"id": 101},
                {"id": 102},
            ],
        ]

        # 初回呼び出し: キャッシュなし
        mock_flask_cache.get.return_value = None
        participants_id_list, participants_mode_list = get_participant_id()

        # 結果の確認
        self.assertEqual(participants_id_list, [1, 2, 101, 102])
        self.assertEqual(
            participants_mode_list, ["single", "team", "team_member", "team_member"]
        )

        # Supabaseが2回呼ばれていることを確認
        self.assertEqual(mock_supabase.get_data.call_count, 2)

        # キャッシュがセットされたことを確認
        mock_flask_cache.set.assert_called_once_with(
            "participant_id_mode_list",
            ([1, 2, 101, 102], ["single", "team", "team_member", "team_member"]),
            timeout=None,
        )

        # キャッシュのテスト: キャッシュあり
        mock_flask_cache.get.return_value = ([10, 20], ["single", "team"])

        # キャッシュから取得
        cached_ids, cached_modes = get_participant_id()
        self.assertEqual(cached_ids, [10, 20])
        self.assertEqual(cached_modes, ["single", "team"])

        # 2回目の呼び出しではSupabaseが呼ばれていないことを確認
        self.assertEqual(mock_supabase.get_data.call_count, 2)
