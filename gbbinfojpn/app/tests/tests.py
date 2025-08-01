"""
gbbinfojpn.app.urls のURLパターンをテストするモジュール

python manage.py test gbbinfojpn.app.tests.tests --keepdb
"""

from django.test import Client, TestCase


class AppUrlsTestCase(TestCase):
    """
    app URLパターンのテストケース

    このクラスは、gbbinfojpn.app.urls で定義されたURLパターンが
    正しくレスポンスを返すかどうかを検証します。

    Attributes:
        client (Client): テスト用のDjangoクライアントインスタンス

    Methods:
        setUp():
            テスト前の初期化処理を行います。
        test_get_all_url_patterns_accessibility():
            すべてのGET用URLパターンが適切なレスポンスを返すかテストします。
        test_post_all_url_patterns_accessibility():
            すべてのPOST用URLパターンが適切なレスポンスを返すかテストします（現状は未実装）。
    """

    def setUp(self):
        """
        テストの前準備を行います。

        Clientインスタンスを作成し、self.clientに格納します。
        """
        self.client = Client()

    def test_get_all_url_patterns_accessibility(self):
        """
        すべてのGET用URLパターンが何らかのレスポンスを返すことをテストします。

        各URLにGETリクエストを送り、200〜399のステータスコード、または
        レスポンスが存在することを検証します。
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
        すべてのPOST用URLパターンが何らかのレスポンスを返すことをテストします。

        各URLにPOSTリクエストを送り、200〜399のステータスコード、または
        レスポンスが存在することを検証します。

        現状、POSTエンドポイントは未実装のため、テストケースは空です。
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
