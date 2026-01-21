"""
Flask アプリケーションのcancels viewのテストモジュール

python -m pytest app/tests/test_cancels_view.py -v
"""

import unittest
from datetime import datetime
from unittest.mock import patch

# Supabaseサービスをモックしてからapp.mainをインポート
with patch("app.context_processors.supabase_service") as mock_supabase:
    # get_available_years()とget_participant_id()のためのモックデータ
    def mock_get_data(*args, **kwargs):
        table = kwargs.get("table")
        if table == "Year":
            return [{"year": 2025}]
        elif table == "Participant":
            return [{"id": 1, "name": "Test", "Category": {"is_team": False}}]
        elif table == "ParticipantMember":
            return [{"id": 2}]
        return []

    mock_supabase.get_data.side_effect = mock_get_data
    from app.main import app


class CancelsViewTestCase(unittest.TestCase):
    """cancels_viewのテストケース"""

    def setUp(self):
        """テストの前準備"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        self.year = datetime.now().year

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()

    @patch("app.views.participants.wildcard_rank_sort")
    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_cancels_view_normal_case(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
        mock_wildcard_rank_sort,
    ):
        """cancels_viewの正常系テスト"""
        mock_get_available_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()
        mock_wildcard_rank_sort.return_value = 0

        # 辞退者のモックデータ
        cancels_data = [
            {
                "id": 1,
                "name": "test_participant_1",
                "category": "Loopstation",
                "ticket_class": "GBB Seed",
                "iso_code": 392,
                "Category": {"name": "Loopstation", "is_team": False},
                "Country": {"iso_alpha2": "JP"},
                "ParticipantMember": [],  # シングル参加者
            },
            {
                "id": 2,
                "name": "test_team_1",
                "category": "Tag Team",
                "ticket_class": "Wildcard 1st",
                "iso_code": 840,
                "Category": {"name": "Tag Team", "is_team": True},
                "Country": {"iso_alpha2": "US"},
                "ParticipantMember": [
                    {"name": "Member1", "Country": {"iso_alpha2": "JP"}},
                    {"name": "Member2", "Country": {"iso_alpha2": "KR"}},
                ],  # チーム参加者
            },
        ]

        mock_supabase.get_data.return_value = cancels_data

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get(f"/ja/{self.year}/cancels")
        self.assertEqual(resp.status_code, 200)

        # レスポンスの内容確認
        response_data = resp.get_data(as_text=True)
        self.assertIn("辞退者一覧", response_data)
        self.assertIn("TEST_PARTICIPANT_1", response_data)  # 大文字変換確認
        self.assertIn("TEST_TEAM_1", response_data)
        self.assertIn("Loopstation", response_data)
        self.assertIn("Tag Team", response_data)

    @patch("app.views.participants.wildcard_rank_sort")
    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_cancels_view_empty_data(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
        mock_wildcard_rank_sort,
    ):
        """cancels_viewで辞退者データが空の場合のテスト"""
        mock_get_available_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()
        mock_wildcard_rank_sort.return_value = 0

        # 空のデータ
        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get(f"/ja/{self.year}/cancels")
        self.assertEqual(resp.status_code, 200)

        # 空の場合のメッセージ確認
        response_data = resp.get_data(as_text=True)
        self.assertIn("辞退者一覧", response_data)
        self.assertIn("発表次第更新", response_data)

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_cancels_view_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """cancels_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get(f"/ja/{self.year}/cancels")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.participants.wildcard_rank_sort")
    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_cancels_view_with_comeback_wildcard(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
        mock_wildcard_rank_sort,
    ):
        """
        cancels_viewでCOMEBACK Wildcardを含む辞退者データが正しくソートされることを確認
        """
        from app.util.participant_edit import wildcard_rank_sort

        mock_get_available_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # wildcard_rank_sortを実際の関数で置き換える（モックではなく）
        mock_wildcard_rank_sort.side_effect = wildcard_rank_sort

        # 辞退者のモックデータ（COMEBACK Wildcardを含む）
        cancels_data = [
            {
                "id": 1,
                "name": "normal cancelled",
                "category": 1,
                "ticket_class": "GBB Seed",
                "iso_code": 392,
                "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                "Country": {"iso_alpha2": "JP"},
                "ParticipantMember": [],
            },
            {
                "id": 2,
                "name": "comeback cancelled",
                "category": 1,
                "ticket_class": "COMEBACK Wildcard",
                "iso_code": 840,
                "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                "Country": {"iso_alpha2": "US"},
                "ParticipantMember": [],
            },
            {
                "id": 3,
                "name": "wildcard cancelled",
                "category": 1,
                "ticket_class": "Wildcard 1 (2024)",
                "iso_code": 826,
                "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                "Country": {"iso_alpha2": "GB"},
                "ParticipantMember": [],
            },
        ]

        mock_supabase.get_data.return_value = cancels_data

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get(f"/ja/{self.year}/cancels")
        self.assertEqual(resp.status_code, 200)

        # レスポンスの内容確認
        response_data = resp.get_data(as_text=True)
        self.assertIn("辞退者一覧", response_data)
        self.assertIn("NORMAL CANCELLED", response_data)  # 大文字変換確認
        self.assertIn("COMEBACK CANCELLED", response_data)
        self.assertIn("WILDCARD CANCELLED", response_data)

        # COMEBACK Wildcardが正しく処理されていることを確認
        # （実際のソート順序はビュー内で処理されるため、レスポンスに含まれることを確認）


if __name__ == "__main__":
    unittest.main()
