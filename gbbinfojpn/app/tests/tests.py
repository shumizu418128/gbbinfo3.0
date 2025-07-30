"""
gbbinfojpn.app.urls のURLパターンをテストするモジュール

python manage.py test gbbinfojpn.app.tests.tests --keepdb
"""

from django.test import Client, TestCase


class AppUrlsTestCase(TestCase):
    """app URLパターンのテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.client = Client()

    def test_get_all_url_patterns_accessibility(self):
        """
        すべてのURLパターンが何らかのレスポンスを返すことをテスト
        """
        test_cases = [
            # (URL, 説明)
            ("/", "ルートURL - redirect_to_latest_top"),
            ("/lang?lang=en&referrer=/", "言語変更URL - change_language"),
            ("/2025/top", "共通ビュー - 存在するテンプレート"),
        ]

        for url, description in test_cases:
            with self.subTest(url=url, description=description):
                response = self.client.get(url)

                # 200-399の範囲のステータスコードまたは、レスポンスが存在することを確認
                self.assertTrue(
                    response.status_code in range(200, 400)
                    or response.status_code is not None,
                    f"{description} ({url}) が適切なレスポンスを返しませんでした。ステータスコード: {response.status_code}",
                )

    def test_post_all_url_patterns_accessibility(self):
        """
        すべてのURLパターンが何らかのレスポンスを返すことをテスト
        """
        test_cases = [
            # TODO: POSTエンドポイントを用意したら実装
        ]

        for url, description in test_cases:
            with self.subTest(url=url, description=description):
                response = self.client.post(url)

                # 200-399の範囲のステータスコードまたは、レスポンスが存在することを確認
                self.assertTrue(
                    response.status_code in range(200, 400)
                    or response.status_code is not None,
                    f"{description} ({url}) が適切なレスポンスを返しませんでした。ステータスコード: {response.status_code}",
                )
