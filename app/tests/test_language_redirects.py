"""
言語プレフィックスがないURLへアクセスしたときに、言語付きURLへリダイレクトされることを検証するテスト
"""

import unittest
from datetime import datetime
from unittest.mock import patch

with patch("app.context_processors.supabase_service") as mock_supabase:
    mock_supabase.get_data.return_value = []
    from app.main import app


class LanguageRedirectTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        self.year = datetime.now().year

    def tearDown(self):
        self.app_context.pop()

    def test_redirects_for_yearly_participants(self):
        """/{year}/participants にアクセスすると /ja/{year}/participants へリダイレクトされる"""
        resp = self.client.get(f"/{self.year}/participants", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        loc = resp.headers.get("Location", "")
        self.assertIn(f"/ja/{self.year}/participants", loc)

    def test_redirects_for_participant_detail(self):
        """/participant_detail/1/single にアクセスすると /ja/participant_detail/1/single へリダイレクトされる"""
        resp = self.client.get("/participant_detail/1/single", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        loc = resp.headers.get("Location", "")
        self.assertIn("/ja/participant_detail/1/single", loc)

    def test_invalid_session_language_redirects_for_various_paths(self):
        """セッションに不適切な言語コードが入っている場合、代表的なパスですべて日本語にリダイレクトされることを検証する"""
        # 不適切な言語をセット
        with self.client.session_transaction() as sess:
            sess["language"] = "xx"  # サポート外の言語コード

        paths = [
            f"/{self.year}/participants",
            f"/{self.year}/result",
            f"/{self.year}/top",
            "/participant_detail/1/single",
        ]

        for path in paths:
            resp = self.client.get(path, follow_redirects=False)
            self.assertIn(resp.status_code, (301, 302), msg=f"{path} did not redirect")
            loc = resp.headers.get("Location", "")
            # セッションが無効な言語なら ja にフォールバックするはず
            self.assertIn("/ja", loc, msg=f"{path} did not redirect to /ja, got {loc}")
