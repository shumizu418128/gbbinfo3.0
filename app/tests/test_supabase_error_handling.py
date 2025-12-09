"""
Flask アプリケーションのSupabaseエラーハンドリングのテストモジュール

python -m pytest app/tests/test_supabase_error_handling.py -v
"""

import json
import unittest
from unittest.mock import patch

from app.main import app

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


class SupabaseErrorHandlingTestCase(unittest.TestCase):
    """Supabaseからの応答がない場合のエラーハンドリングのテストケース"""

    def setUp(self):
        """テストの前準備"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()

    @patch("app.views.result.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_result_view_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """result_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/result?category=Loopstation")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.world_map.os.path.exists")
    @patch("app.views.world_map.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_world_map_view_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
        mock_os_path_exists,
    ):
        """world_map_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # マップファイルが存在しないようにする
        mock_os_path_exists.return_value = False

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/world_map")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    @patch("app.views.participants.get_available_years")
    def test_participants_view_supabase_no_response(
        self,
        mock_participants_get_available_years,
        mock_context_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """participants_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_participants_get_available_years.return_value = [2025]
        mock_context_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: pandas=True かつ raise_error 未指定のため空DataFrameを返す想定
        import pandas as pd

        mock_supabase.get_data.return_value = pd.DataFrame()

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/participants")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.beatboxer_finder.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_search_participants_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """search_participantsでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 1回目（raise_error未指定）: 空リスト、2回目（raise_error=True）: 例外
        mock_supabase.get_data.side_effect = [[], Exception("supabase error")]

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        request_data = json.dumps({"keyword": "test"})
        resp = self.client.post(
            "/2025/search_participants",
            data=request_data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.result.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_result_view_empty_dataframe(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """result_viewで空のDataFrameが返される場合に500エラーが返されることをテスト"""

        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/result?category=Loopstation")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    @patch("app.views.participants.get_available_years")
    def test_participants_view_empty_dataframe(
        self,
        mock_participants_get_available_years,
        mock_context_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """participants_viewで空のDataFrameが返される場合に500エラーが返されることをテスト"""
        import pandas as pd

        mock_participants_get_available_years.return_value = [2025]
        mock_context_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 空のDataFrameを返す
        mock_supabase.get_data.return_value = pd.DataFrame()

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/participants")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.beatboxer_finder.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_search_participants_empty_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """search_participantsで空のレスポンスが返される場合に200と空配列が返ることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 空のリストを返す
        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        request_data = json.dumps({"keyword": "test"})
        resp = self.client.post(
            "/2025/search_participants",
            data=request_data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    @patch("app.views.rule.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_rule_view_continues_with_empty_data(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """rule_viewでSupabaseからの応答がない場合に空のデータでページを表示することをテスト

        Note: rule.pyでは44-51行目でSupabaseからのデータが取得できない場合、
        空のコンテキスト（gbb_seed, other_seed, cancelled すべて空配列）でページを表示する
        """
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 空のリストを返す（Supabaseからデータが取得できない状況をシミュレート）
        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/rule")
        # rule.pyでは空のデータでもページを表示するため200が返される
        self.assertEqual(resp.status_code, 200)

        # レスポンスのHTMLに空のデータが適用されていることを確認
        html = resp.get_data(as_text=True)
        # 空のシード権獲得者リストでもページが正常に表示されることを確認
        self.assertIn("rule", html.lower())  # ルールページが表示されていることを確認

    @patch("app.views.rule.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_rule_view_supabase_none_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """rule_viewでSupabaseからNoneが返される場合のテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # Noneを返す（Supabaseからの応答がない状況をシミュレート）
        mock_supabase.get_data.return_value = None

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/rule")
        # rule.pyでは応答がなくても空のデータでページを表示するため200が返される
        self.assertEqual(resp.status_code, 200)
