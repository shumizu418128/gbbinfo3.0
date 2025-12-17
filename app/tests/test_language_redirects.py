"""
言語プレフィックスがないURLへアクセスしたときに、言語付きURLへリダイレクトされることを検証するテスト
"""

import unittest
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

    def tearDown(self):
        self.app_context.pop()

    def test_redirects_for_yearly_participants(self):
        """/2025/participants にアクセスすると /ja/2025/participants へリダイレクトされる"""
        resp = self.client.get("/2025/participants", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        loc = resp.headers.get("Location", "")
        self.assertIn("/ja/2025/participants", loc)

    def test_redirects_for_participant_detail(self):
        """/participant_detail/1/single にアクセスすると /ja/participant_detail/1/single へリダイレクトされる"""
        resp = self.client.get("/participant_detail/1/single", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        loc = resp.headers.get("Location", "")
        self.assertIn("/ja/participant_detail/1/single", loc)
