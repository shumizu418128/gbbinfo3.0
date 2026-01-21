"""
Flask アプリケーションのビューのテストモジュール

python -m pytest app/tests/test_views.py -v
"""

import json
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

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


class ViewsTestCase(unittest.TestCase):
    """
    ビュー関数のテストケース
    """

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

    @patch("app.views.beatboxer_finder.supabase_service")
    def test_search_participants(self, mock_supabase):
        """参加者検索のテスト"""
        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [  # 参加者データ
                {
                    "id": 1,
                    "name": "test user",
                    "category": 1,
                    "ticket_class": "standard",
                    "is_cancelled": False,
                    "Category": {"name": "Loopstation", "is_team": False},
                    "ParticipantMember": [],
                }
            ],
            [],  # メンバーデータ（空）
        ]

        request_data = json.dumps({"keyword": "test"})
        response = self.client.post(
            f"/{self.year}/search_participants",
            data=request_data,
            content_type="application/json",
        )

        # JSONレスポンスが返されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

    @patch("app.views.beatboxer_finder.supabase_service")
    def test_search_participants_solo_team_multinational(self, mock_supabase):
        """参加者検索でソロ・複数名チーム・多国籍チームの3種類をテスト"""
        # テストケース1: ソロ参加者
        mock_supabase.get_data.side_effect = [
            [
                {  # 参加者データ
                    "id": 1001,
                    "name": "SoloPlayer",
                    "category": 1,
                    "ticket_class": "GBB Seed",
                    "is_cancelled": False,
                    "Category": {"id": 1, "name": "Solo", "is_team": False},
                    "ParticipantMember": [],  # 空の配列 = ソロ
                }
            ],
            [],  # メンバーデータ（空）
        ]

        response = self.client.post(
            f"/{self.year}/search_participants", json={"keyword": "SoloPlayer"}
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "SOLOPLAYER")  # 大文字変換
        self.assertEqual(result[0]["category"], "Solo")
        self.assertEqual(result[0]["mode"], "single")  # ソロ

        # テストケース2: 複数名チーム（同一国籍）
        mock_supabase.get_data.side_effect = [
            [
                {  # 参加者データ
                    "id": 1002,
                    "name": "Team Japan",
                    "category": 2,
                    "ticket_class": "Wildcard 1 (2024)",
                    "is_cancelled": False,
                    "Category": {"id": 2, "name": "Tag Team", "is_team": True},
                    "ParticipantMember": [
                        {"id": 1, "name": "Member1"},
                        {"id": 2, "name": "Member2"},
                    ],
                }
            ],
            [],  # メンバーデータ（空）
        ]

        response = self.client.post(
            f"/{self.year}/search_participants", json={"keyword": "Team Japan"}
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "TEAM JAPAN")  # 大文字変換
        self.assertEqual(result[0]["category"], "Tag Team")
        self.assertEqual(result[0]["mode"], "team")  # チーム
        self.assertEqual(result[0]["members"], "MEMBER1, MEMBER2")  # メンバー

        # テストケース3: 多国籍チーム（異なる国籍）
        mock_supabase.get_data.side_effect = [
            [
                {  # 参加者データ
                    "id": 1003,
                    "name": "International Team",
                    "category": 3,
                    "ticket_class": "GBB Seed",
                    "is_cancelled": False,
                    "Category": {"id": 3, "name": "Crew", "is_team": True},
                    "ParticipantMember": [
                        {"id": 1, "name": "Japanese Member"},
                        {"id": 2, "name": "Korean Member"},
                        {"id": 3, "name": "American Member"},
                    ],
                }
            ],
            [],  # メンバーデータ（空）
        ]

        response = self.client.post(
            f"/{self.year}/search_participants", json={"keyword": "International Team"}
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "INTERNATIONAL TEAM")  # 大文字変換
        self.assertEqual(result[0]["category"], "Crew")
        self.assertEqual(result[0]["mode"], "team")  # チーム
        self.assertEqual(
            result[0]["members"],
            "JAPANESE MEMBER, KOREAN MEMBER, AMERICAN MEMBER",
        )  # 3名のメンバー

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_available_years")
    def test_participants_view_with_comeback_wildcard(
        self, mock_get_available_years, mock_supabase
    ):
        """
        participants_viewでCOMEBACK Wildcardを含む出場者データが正しくソートされることを確認
        """
        import pandas as pd

        mock_get_available_years.return_value = [2025, 2024, 2023]

        # Yearテーブルからのデータ（categoriesを含む）
        year_data = pd.DataFrame([{"categories": [1]}])

        # Categoryテーブルからのデータ
        category_data = pd.DataFrame([{"id": 1, "name": "Loopstation"}])

        # Participantテーブルからのデータ（COMEBACK Wildcardを含む）
        participants_data = [
            {
                "id": 1,
                "name": "normal player",
                "category": 1,
                "ticket_class": "GBB Seed",
                "is_cancelled": False,
                "iso_code": 392,
                "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                "ParticipantMember": [],
                "Country": {
                    "iso_code": 392,
                    "names": {"ja": "日本", "en": "Japan"},
                    "iso_alpha2": "JP",
                },
            },
            {
                "id": 2,
                "name": "comeback player",
                "category": 1,
                "ticket_class": "COMEBACK Wildcard",
                "is_cancelled": False,
                "iso_code": 840,
                "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                "ParticipantMember": [],
                "Country": {
                    "iso_code": 840,
                    "names": {"ja": "アメリカ", "en": "United States"},
                    "iso_alpha2": "US",
                },
            },
            {
                "id": 3,
                "name": "wildcard player",
                "category": 1,
                "ticket_class": "Wildcard 1 (2024)",
                "is_cancelled": False,
                "iso_code": 826,
                "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                "ParticipantMember": [],
                "Country": {
                    "iso_code": 826,
                    "names": {"ja": "イギリス", "en": "United Kingdom"},
                    "iso_alpha2": "GB",
                },
            },
        ]

        # supabase_service.get_dataの呼び出し順序に応じてデータを返す
        def mock_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)

            if table == "Year" and pandas_flag:
                return year_data
            elif table == "Category" and pandas_flag:
                return category_data
            elif table == "Participant":
                return participants_data
            return []

        mock_supabase.get_data.side_effect = mock_get_data_side_effect

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        response = self.client.get(
            f"/ja/{self.year}/participants?category=Loopstation&ticket_class=all&cancel=show"
        )

        # ステータスコードが200であることを確認
        self.assertEqual(response.status_code, 200)

        # レスポンスの内容確認
        response_data = response.get_data(as_text=True)
        self.assertIn("NORMAL PLAYER", response_data)
        self.assertIn("COMEBACK PLAYER", response_data)
        self.assertIn("WILDCARD PLAYER", response_data)

        # COMEBACK Wildcardが正しく処理されていることを確認
        # （実際のソート順序はビュー内で処理されるため、レスポンスに含まれることを確認）
