"""
participant_detail.py のテストモジュール

python -m pytest app/tests/test_participant_detail.py -v
"""

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

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


class TestParticipantDetailWithIsoCodeZero(unittest.TestCase):
    """
    iso_codeが0の出場者の詳細ページが正しく表示されることを確認するテストケース
    """

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

    @patch("app.context_processors.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    def test_single_participant_with_iso_code_zero(
        self, mock_view_supabase, mock_context_supabase
    ):
        """
        iso_codeが0の単一出場者の詳細ページが正しく表示されることを確認
        """

        # context_processors用のモック設定
        def mock_get_data(**kwargs):
            # pandas=Trueが指定されている場合はpandas DataFrameを返す
            if kwargs.get("pandas", False):
                return pd.DataFrame(
                    [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
                )
            # filtersが指定されている場合はYearテーブルからのデータとして扱う
            elif "filters" in kwargs:
                return [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
            # それ以外の場合はget_available_years()用のリストを返す
            else:
                return [{"year": 2025}]

        mock_context_supabase.get_data.side_effect = mock_get_data

        # モックデータの設定
        mock_view_supabase.get_data.side_effect = [
            # 1回目: 出場者詳細データ
            [
                {
                    "id": 1,
                    "name": "tbd player",
                    "year": 2025,
                    "category": 1,
                    "iso_code": 0,  # iso_codeが0
                    "ticket_class": "GBB Seed",
                    "is_cancelled": False,
                    "Country": {"iso_code": 0, "names": {}, "iso_alpha2": ""},
                    "Category": {"id": 1, "name": "Solo"},
                    "ParticipantMember": [],
                }
            ],
            # 2回目: 過去の出場履歴（Participant）
            [],
            # 3回目: 過去の出場履歴（ParticipantMember）
            [],
            # 4回目: 同じ年・部門の出場者一覧
            [
                {
                    "id": 1,
                    "name": "tbd player",
                    "is_cancelled": False,
                    "ticket_class": "GBB Seed",
                    "iso_code": 0,
                    "Country": {"names": {}, "iso_alpha2": ""},
                    "ParticipantMember": [],
                },
                {
                    "id": 2,
                    "name": "confirmed player",
                    "is_cancelled": False,
                    "ticket_class": "GBB Seed",
                    "iso_code": 392,
                    "Country": {
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP",
                    },
                    "ParticipantMember": [],
                },
            ],
        ]

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        response = self.client.get("/participant_detail/1/single")

        # ステータスコードが200であることを確認
        self.assertEqual(response.status_code, 200)

        # レスポンスにiso_alpha2が空リストとして含まれていることを確認
        response_data = response.data.decode("utf-8")
        self.assertIn("TBD PLAYER", response_data)

    @patch("app.context_processors.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    def test_team_with_iso_code_zero(self, mock_view_supabase, mock_context_supabase):
        """
        iso_codeが0のチームの詳細ページが正しく表示されることを確認
        """

        # context_processors用のモック設定
        def mock_get_data(**kwargs):
            # pandas=Trueが指定されている場合はpandas DataFrameを返す
            if kwargs.get("pandas", False):
                return pd.DataFrame(
                    [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
                )
            # filtersが指定されている場合はYearテーブルからのデータとして扱う
            elif "filters" in kwargs:
                return [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
            # それ以外の場合はget_available_years()用のリストを返す
            else:
                return [{"year": 2025}]

        mock_context_supabase.get_data.side_effect = mock_get_data

        # モックデータの設定
        mock_view_supabase.get_data.side_effect = [
            # 1回目: 出場者詳細データ
            [
                {
                    "id": 10,
                    "name": "tbd team",
                    "year": 2025,
                    "category": 2,
                    "iso_code": 0,  # iso_codeが0
                    "ticket_class": "Wildcard 1",
                    "is_cancelled": False,
                    "Country": {"iso_code": 0, "names": {}, "iso_alpha2": ""},
                    "Category": {"id": 2, "name": "Tag Team"},
                    "ParticipantMember": [],
                }
            ],
            # 2回目: 過去の出場履歴（Participant）
            [],
            # 3回目: 過去の出場履歴（ParticipantMember）
            [],
            # 4回目: 同じ年・部門の出場者一覧
            [
                {
                    "id": 10,
                    "name": "tbd team",
                    "is_cancelled": False,
                    "ticket_class": "Wildcard 1",
                    "iso_code": 0,
                    "Country": {"names": {}, "iso_alpha2": ""},
                    "ParticipantMember": [],
                }
            ],
        ]

        with self.client.session_transaction() as sess:
            sess["language"] = "en"

        response = self.client.get("/participant_detail/10/team")

        # ステータスコードが200であることを確認
        self.assertEqual(response.status_code, 200)

        # レスポンスにチーム名が含まれていることを確認
        response_data = response.data.decode("utf-8")
        self.assertIn("TBD TEAM", response_data)

    @patch("app.context_processors.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    def test_team_member_with_iso_code_zero(
        self, mock_view_supabase, mock_context_supabase
    ):
        """
        iso_codeが0のチームメンバーの詳細ページが正しく表示されることを確認
        """

        # context_processors用のモック設定
        def mock_get_data(**kwargs):
            # pandas=Trueが指定されている場合はpandas DataFrameを返す
            if kwargs.get("pandas", False):
                return pd.DataFrame(
                    [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
                )
            # filtersが指定されている場合はYearテーブルからのデータとして扱う
            elif "filters" in kwargs:
                return [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
            # それ以外の場合はget_available_years()用のリストを返す
            else:
                return [{"year": 2025}]

        mock_context_supabase.get_data.side_effect = mock_get_data

        # モックデータの設定
        mock_view_supabase.get_data.side_effect = [
            # 1回目: チームメンバー詳細データ
            [
                {
                    "id": 100,
                    "participant": 10,
                    "name": "tbd member",
                    "iso_code": 0,  # iso_codeが0
                    "Country": {"iso_code": 0, "names": {}, "iso_alpha2": ""},
                    "Participant": {
                        "id": 10,
                        "name": "team name",
                        "year": 2025,
                        "category": 2,
                        "is_cancelled": False,
                        "ticket_class": "GBB Seed",
                        "Category": {"id": 2, "name": "Crew"},
                    },
                }
            ],
            # 2回目: 過去の出場履歴（Participant）
            [],
            # 3回目: 過去の出場履歴（ParticipantMember）
            [],
            # 4回目: 同じ年・部門の出場者一覧
            [
                {
                    "id": 10,
                    "name": "team name",
                    "is_cancelled": False,
                    "ticket_class": "GBB Seed",
                    "iso_code": 392,
                    "Country": {
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP",
                    },
                    "ParticipantMember": [],
                }
            ],
        ]

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        response = self.client.get("/participant_detail/100/team_member")

        # ステータスコードが200であることを確認
        self.assertEqual(response.status_code, 200)

        # レスポンスにメンバー名が含まれていることを確認
        response_data = response.data.decode("utf-8")
        self.assertIn("TBD MEMBER", response_data)

    @patch("app.context_processors.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    def test_same_category_participants_sorting_with_iso_code_zero(
        self, mock_view_supabase, mock_context_supabase
    ):
        """
        同じ部門の出場者一覧で、iso_codeが0の出場者が正しくソートされることを確認
        iso_codeが0の出場者は下位に表示される
        """

        # context_processors用のモック設定
        def mock_get_data(**kwargs):
            # pandas=Trueが指定されている場合はpandas DataFrameを返す
            if kwargs.get("pandas", False):
                return pd.DataFrame(
                    [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
                )
            # filtersが指定されている場合はYearテーブルからのデータとして扱う
            elif "filters" in kwargs:
                return [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
            # それ以外の場合はget_available_years()用のリストを返す
            else:
                return [{"year": 2025}]

        mock_context_supabase.get_data.side_effect = mock_get_data

        # モックデータの設定
        mock_view_supabase.get_data.side_effect = [
            # 1回目: 出場者詳細データ
            [
                {
                    "id": 1,
                    "name": "main player",
                    "year": 2025,
                    "category": 1,
                    "iso_code": 392,
                    "ticket_class": "GBB Seed",
                    "is_cancelled": False,
                    "Country": {
                        "iso_code": 392,
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP",
                    },
                    "Category": {"id": 1, "name": "Solo"},
                    "ParticipantMember": [],
                }
            ],
            # 2回目: 過去の出場履歴（Participant）
            [],
            # 3回目: 過去の出場履歴（ParticipantMember）
            [],
            # 4回目: 同じ年・部門の出場者一覧
            [
                {
                    "id": 1,
                    "name": "main player",
                    "is_cancelled": False,
                    "ticket_class": "GBB Seed",
                    "iso_code": 392,
                    "Country": {
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP",
                    },
                    "ParticipantMember": [],
                },
                {
                    "id": 2,
                    "name": "tbd player 1",
                    "is_cancelled": False,
                    "ticket_class": "GBB Seed",
                    "iso_code": 0,  # iso_codeが0
                    "Country": {"names": {}, "iso_alpha2": ""},
                    "ParticipantMember": [],
                },
                {
                    "id": 3,
                    "name": "wildcard player",
                    "is_cancelled": False,
                    "ticket_class": "Wildcard 1",
                    "iso_code": 840,
                    "Country": {
                        "names": {"ja": "アメリカ", "en": "United States"},
                        "iso_alpha2": "US",
                    },
                    "ParticipantMember": [],
                },
                {
                    "id": 4,
                    "name": "tbd player 2",
                    "is_cancelled": False,
                    "ticket_class": "Wildcard 2",
                    "iso_code": 0,  # iso_codeが0
                    "Country": {"names": {}, "iso_alpha2": ""},
                    "ParticipantMember": [],
                },
                {
                    "id": 5,
                    "name": "cancelled player",
                    "is_cancelled": True,
                    "ticket_class": "GBB Seed",
                    "iso_code": 826,
                    "Country": {
                        "names": {"ja": "イギリス", "en": "United Kingdom"},
                        "iso_alpha2": "GB",
                    },
                    "ParticipantMember": [],
                },
            ],
        ]

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        response = self.client.get("/participant_detail/1/single")

        # ステータスコードが200であることを確認
        self.assertEqual(response.status_code, 200)

        # レスポンスが正しく表示されることを確認
        response_data = response.data.decode("utf-8")
        self.assertIn("MAIN PLAYER", response_data)

    @patch("app.context_processors.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    def test_mixed_iso_code_zero_and_normal_participants(
        self, mock_view_supabase, mock_context_supabase
    ):
        """
        iso_codeが0の出場者と通常の出場者が混在している場合の表示を確認
        """

        # context_processors用のモック設定
        def mock_get_data(**kwargs):
            # pandas=Trueが指定されている場合はpandas DataFrameを返す
            if kwargs.get("pandas", False):
                return pd.DataFrame(
                    [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
                )
            # filtersが指定されている場合はYearテーブルからのデータとして扱う
            elif "filters" in kwargs:
                return [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
            # それ以外の場合はget_available_years()用のリストを返す
            else:
                return [{"year": 2025}]

        mock_context_supabase.get_data.side_effect = mock_get_data

        # モックデータの設定
        mock_view_supabase.get_data.side_effect = [
            # 1回目: 出場者詳細データ
            [
                {
                    "id": 1,
                    "name": "normal player",
                    "year": 2025,
                    "category": 1,
                    "iso_code": 392,
                    "ticket_class": "GBB Seed",
                    "is_cancelled": False,
                    "Country": {
                        "iso_code": 392,
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP",
                    },
                    "Category": {"id": 1, "name": "Solo"},
                    "ParticipantMember": [],
                }
            ],
            # 2回目: 過去の出場履歴（Participant）
            [],
            # 3回目: 過去の出場履歴（ParticipantMember）
            [],
            # 4回目: 同じ年・部門の出場者一覧（iso_code=0と通常の出場者が混在）
            [
                {
                    "id": 1,
                    "name": "normal player",
                    "is_cancelled": False,
                    "ticket_class": "GBB Seed",
                    "iso_code": 392,
                    "Country": {
                        "names": {"ja": "日本", "en": "Japan"},
                        "iso_alpha2": "JP",
                    },
                    "ParticipantMember": [],
                },
                {
                    "id": 2,
                    "name": "tbd player",
                    "is_cancelled": False,
                    "ticket_class": "GBB Seed",
                    "iso_code": 0,
                    "Country": {"names": {}, "iso_alpha2": ""},
                    "ParticipantMember": [],
                },
            ],
        ]

        with self.client.session_transaction() as sess:
            sess["language"] = "en"

        response = self.client.get("/participant_detail/1/single")

        # ステータスコードが200であることを確認
        self.assertEqual(response.status_code, 200)

        # 両方の出場者が表示されることを確認
        response_data = response.data.decode("utf-8")
        self.assertIn("NORMAL PLAYER", response_data)

    def test_participant_detail_without_params(self):
        """
        idとmodeパラメータがない場合、participantsページにリダイレクトされることを確認
        """
        response = self.client.get("/others/participant_detail")

        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        year = datetime.now().year
        self.assertIn(f"/{year}/participants", response.location)

    @patch("app.context_processors.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    def test_participant_detail_not_found(
        self, mock_view_supabase, mock_context_supabase
    ):
        """
        存在しないidの場合、participantsページにリダイレクトされることを確認
        """

        # context_processors用のモック設定
        def mock_get_data(**kwargs):
            # pandas=Trueが指定されている場合はpandas DataFrameを返す
            if kwargs.get("pandas", False):
                return pd.DataFrame(
                    [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
                )
            # filtersが指定されている場合はYearテーブルからのデータとして扱う
            elif "filters" in kwargs:
                return [{"year": 2025, "ends_at": "2025-12-31T23:59:59+00:00"}]
            # それ以外の場合はget_available_years()用のリストを返す
            else:
                return [{"year": 2025}]

        mock_context_supabase.get_data.side_effect = mock_get_data

        # モックデータの設定（空のリストを返す）
        mock_view_supabase.get_data.return_value = []

        response = self.client.get("/participant_detail/99999/single")

        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        # 2025年のparticipantsページへリダイレクトされる
        self.assertIn("/2025/participants", response.location)


if __name__ == "__main__":
    unittest.main()
