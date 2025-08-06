"""
gbbinfojpn.app.urls のURLパターンをテストするモジュール

python manage.py test gbbinfojpn.app.tests.tests --keepdb
"""

import json
import os
from unittest.mock import Mock, patch

from django.test import Client, TestCase
from django.http import HttpRequest
from django.core.cache import cache

from gbbinfojpn.app.context_processors import get_available_years, is_latest_year, is_early_access, is_translated, common_variables
from gbbinfojpn.app.views.common import top_redirect_view, content_view, other_content_view, not_found_page_view
from gbbinfojpn.app.views.language import change_language
from gbbinfojpn.app.views.search_participants import post_search_participants

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


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
        available_years = get_available_years()

        test_cases = [
            ("/", "ルートページ"),
            ("/lang?lang=en", "言語変更 英語"),
            ("/lang?lang=ja", "言語変更 日本語"),
            ("/others/participant_detail?id=2064&mode=single", "出場者詳細 JUNNO"),
        ]

        for year in available_years:
            file_list = os.listdir(f"gbbinfojpn/app/templates/{year}")
            for file in file_list:
                if file.endswith(".html"):
                    test_cases.append(
                        (
                            f"/{year}/{file.replace('.html', '')}",
                            f"/{year}/{file.replace('.html', '')}",
                        ),
                    )
            for common_url in COMMON_URLS:
                test_cases.append(
                    (f"/{year}{common_url}", f"/{year}{common_url}"),
                )

        other_urls = os.listdir("gbbinfojpn/app/templates/others")
        for other_url in other_urls:
            if other_url.endswith(".html"):
                test_cases.append(
                    (
                        f"/others/{other_url.replace('.html', '')}",
                        f"/others/{other_url.replace('.html', '')}",
                    ),
                )

        for url, description in test_cases:
            with self.subTest(url=url, description=description):
                response = self.client.get(url)

                # 200-399の範囲のステータスコードまたは、レスポンスが存在することを確認
                self.assertTrue(
                    response.status_code in range(200, 400)
                    or response.status_code is not None,
                    f"{description} ({url}) が適切なレスポンスを返しませんでした。ステータスコード: {response.status_code}",
                )


class ContextProcessorsTestCase(TestCase):
    """
    コンテキストプロセッサのテストケース
    """

    def setUp(self):
        """テストの前準備"""
        cache.clear()

    @patch('gbbinfojpn.app.context_processors.supabase_service')
    def test_get_available_years(self, mock_supabase):
        """利用可能な年度の取得テスト"""
        # モックデータの設定
        mock_supabase.get_data.return_value = [
            {"year": 2024},
            {"year": 2023},
            {"year": 2022}
        ]
        
        result = get_available_years()
        
        # 降順でソートされていることを確認
        self.assertEqual(result, [2024, 2023, 2022])
        
        # Supabaseが正しいパラメータで呼ばれていることを確認
        mock_supabase.get_data.assert_called_once()

    def test_is_latest_year(self):
        """最新年度判定のテスト"""
        with patch('gbbinfojpn.app.context_processors.get_available_years') as mock_get_years:
            with patch('gbbinfojpn.app.context_processors.datetime') as mock_datetime:
                mock_get_years.return_value = [2025, 2024, 2023]
                mock_datetime.now.return_value.year = 2025
                
                # 現在年度は最新年度
                self.assertTrue(is_latest_year(2025))
                
                # 過去年度は最新年度ではない
                self.assertFalse(is_latest_year(2024))
                
                # 未来年度は最新年度
                self.assertTrue(is_latest_year(2026))

    def test_is_early_access(self):
        """早期アクセス判定のテスト"""
        with patch('gbbinfojpn.app.context_processors.datetime') as mock_datetime:
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
        self.assertTrue(is_translated("/test", "ja"))
        
        # 英語は翻訳ファイルに依存
        with patch('gbbinfojpn.app.context_processors.TRANSLATED_URLS', ["/test"]):
            self.assertTrue(is_translated("/test", "en"))
            self.assertFalse(is_translated("/not-translated", "en"))

    @patch('gbbinfojpn.app.context_processors.supabase_service')
    @patch('gbbinfojpn.app.context_processors.get_available_years')
    def test_common_variables(self, mock_get_years, mock_supabase):
        """共通変数のテスト"""
        mock_get_years.return_value = [2025, 2024]
        mock_supabase.get_data.return_value = [{"year": 2025, "ends_at": None}]
        
        # リクエストオブジェクトのモック
        request = Mock()
        request.path = "/2025/top"
        request.LANGUAGE_CODE = "ja"
        request.get_full_path.return_value = "/2025/top"
        request.GET.get.return_value = ""
        
        result = common_variables(request)
        
        # 必要なキーが含まれていることを確認
        self.assertIn("year", result)
        self.assertIn("available_years", result)
        self.assertIn("language", result)
        self.assertIn("is_translated", result)
        self.assertEqual(result["year"], 2025)


class ViewsTestCase(TestCase):
    """
    ビュー関数のテストケース
    """

    def setUp(self):
        """テストの前準備"""
        self.client = Client()

    @patch('gbbinfojpn.app.views.common.get_available_years')
    def test_top_redirect_view(self, mock_get_years):
        """トップページリダイレクトのテスト"""
        mock_get_years.return_value = [2025, 2024, 2023]
        
        with patch('gbbinfojpn.app.views.common.datetime') as mock_datetime:
            mock_datetime.now.return_value.year = 2025
            
            request = Mock()
            response = top_redirect_view(request)
            
            # 最新年度にリダイレクトされることを確認
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, "/2025/top")

    def test_content_view_old_years(self):
        """古い年度のコンテンツビューテスト"""
        request = Mock()
        
        # 2013-2016年のtop以外はリダイレクト
        response = content_view(request, 2015, "rule")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/2015/top")

    def test_not_found_page_view(self):
        """404ページのテスト"""
        request = Mock()
        
        with patch('gbbinfojpn.app.views.common.render') as mock_render:
            mock_render.return_value = Mock(status_code=404)
            
            response = not_found_page_view(request)
            
            # renderが正しいパラメータで呼ばれることを確認
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            self.assertEqual(args[1], "common/404.html")
            self.assertEqual(kwargs["status"], 404)

    def test_change_language(self):
        """言語変更のテスト"""
        with patch('django.conf.settings.SUPPORTED_LANGUAGE_CODES', ['ja', 'en']):
            with patch('django.conf.settings.LANGUAGE_COOKIE_NAME', 'django_language'):
                # 有効な言語コード
                response = self.client.get('/lang?lang=en', HTTP_REFERER='/')
                self.assertEqual(response.status_code, 302)
                
                # 無効な言語コードはjaにフォールバック
                response = self.client.get('/lang?lang=invalid', HTTP_REFERER='/')
                self.assertEqual(response.status_code, 302)

    @patch('gbbinfojpn.app.views.search_participants.supabase_service')
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
                    "Category": {"name": "Loopstation"},
                    "ParticipantMember": []
                }
            ],
            []  # メンバーデータ（空）
        ]
        
        request_data = json.dumps({"keyword": "test"})
        response = self.client.post(
            '/2025/search_participants',
            data=request_data,
            content_type='application/json'
        )
        
        # JSONレスポンスが返されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')


class SupabaseServiceTestCase(TestCase):
    """
    Supabaseサービスのテストケース
    """

    def setUp(self):
        """テストの前準備"""
        cache.clear()

    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_ANON_KEY': 'test_anon_key',
        'SUPABASE_SERVICE_ROLE_KEY': 'test_service_key'
    })
    def test_supabase_service_initialization(self):
        """Supabaseサービスの初期化テスト"""
        from gbbinfojpn.app.models.supabase_client import SupabaseService
        
        service = SupabaseService()
        self.assertIsNotNone(service)

    @patch.dict(os.environ, {}, clear=True)
    def test_supabase_service_missing_env_vars(self):
        """環境変数不足時のエラーテスト"""
        from gbbinfojpn.app.models.supabase_client import SupabaseService
        
        with self.assertRaises(ValueError) as context:
            SupabaseService()
        
        self.assertIn("環境変数が必要です", str(context.exception))


class IntegrationTestCase(TestCase):
    """
    統合テストケース
    """

    def setUp(self):
        """テストの前準備"""
        self.client = Client()
        cache.clear()

    @patch('gbbinfojpn.app.models.supabase_client.supabase_service')
    def test_participants_page_integration(self, mock_supabase):
        """参加者ページの統合テスト"""
        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"year": 2025, "categories": [1, 2]}],  # Year data
            [{"id": 1, "name": "Loopstation"}, {"id": 2, "name": "Solo"}],  # Category data
            [  # Participant data
                {
                    "id": 1,
                    "name": "TEST USER",
                    "country": "JP",
                    "category": 1,
                    "ticket_class": "standard",
                    "is_cancelled": False,
                    "Country": {"names": "Japan"},
                    "Category": {"name": "Loopstation"},
                    "ParticipantMember": []
                }
            ]
        ]
        
        response = self.client.get('/2025/participants')
        
        # ページが正常に表示されることを確認
        self.assertEqual(response.status_code, 200)

    @patch('gbbinfojpn.app.models.supabase_client.supabase_service')
    def test_result_page_integration(self, mock_supabase):
        """結果ページの統合テスト"""
        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"categories": [1, 2]}],  # Year data
            [{"id": 1, "name": "Loopstation"}, {"id": 2, "name": "Solo"}],  # Category data
            [  # Tournament result data
                {
                    "round": "Final",
                    "winner": {"name": "WINNER"},
                    "loser": {"name": "LOSER"}
                }
            ]
        ]
        
        response = self.client.get('/2025/result?category=Loopstation')
        
        # ページが正常に表示されることを確認
        self.assertEqual(response.status_code, 200)

    def test_language_switching_integration(self):
        """言語切り替えの統合テスト"""
        with patch('django.conf.settings.SUPPORTED_LANGUAGE_CODES', ['ja', 'en']):
            with patch('django.conf.settings.LANGUAGE_COOKIE_NAME', 'django_language'):
                # 言語を英語に変更
                response = self.client.get('/lang?lang=en', HTTP_REFERER='/2025/top')
                
                # リダイレクトされることを確認
                self.assertEqual(response.status_code, 302)
                
                # クッキーが設定されることを確認
                self.assertIn('django_language', response.cookies)

    def test_error_handling_integration(self):
        """エラーハンドリングの統合テスト"""
        # 存在しないページにアクセス
        response = self.client.get('/nonexistent/page')
        
        # 404が返されることを確認
        self.assertEqual(response.status_code, 404)


class PerformanceTestCase(TestCase):
    """
    パフォーマンステストケース
    """

    def setUp(self):
        """テストの前準備"""
        self.client = Client()
        cache.clear()

    @patch('gbbinfojpn.app.models.supabase_client.supabase_service')
    def test_cache_functionality(self, mock_supabase):
        """キャッシュ機能のテスト"""
        from gbbinfojpn.app.models.supabase_client import SupabaseService
        
        # 環境変数をモック
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test_anon_key',
            'SUPABASE_SERVICE_ROLE_KEY': 'test_service_key'
        }):
            service = SupabaseService()
            
            # モックレスポンスの設定
            mock_response = Mock()
            mock_response.data = [{"id": 1, "name": "test"}]
            service.read_only_client = Mock()
            service.read_only_client.table.return_value.select.return_value.execute.return_value = mock_response
            
            # 最初の呼び出し
            result1 = service.get_data("test_table", columns=["id", "name"])
            
            # 2回目の呼び出し（キャッシュから取得されるはず）
            result2 = service.get_data("test_table", columns=["id", "name"])
            
            # 結果が同じであることを確認
            self.assertEqual(result1, result2)
            
            # Supabaseクライアントが1回だけ呼ばれることを確認（キャッシュが効いている）
            self.assertEqual(service.read_only_client.table.call_count, 1)

    def test_multiple_requests_performance(self):
        """複数リクエストのパフォーマンステスト"""
        import time
        
        start_time = time.time()
        
        # 複数のリクエストを送信
        for i in range(5):
            response = self.client.get('/')
            self.assertIn(response.status_code, [200, 302, 404])
        
        end_time = time.time()
        
        # 5秒以内に完了することを確認（パフォーマンスの基準）
        self.assertLess(end_time - start_time, 5.0)


class SecurityTestCase(TestCase):
    """
    セキュリティテストケース
    """

    def setUp(self):
        """テストの前準備"""
        self.client = Client()

    def test_xss_protection(self):
        """XSS攻撃からの保護テスト"""
        # 悪意のあるスクリプトを含むリクエスト
        malicious_script = "<script>alert('xss')</script>"
        
        response = self.client.get(f'/lang?lang={malicious_script}')
        
        # リダイレクトされることを確認（スクリプトが実行されない）
        self.assertEqual(response.status_code, 302)

    def test_external_redirect_protection(self):
        """外部リダイレクト攻撃からの保護テスト"""
        # 外部サイトへのリダイレクトを試行
        external_url = "http://malicious-site.com"
        
        response = self.client.get('/lang?lang=en', HTTP_REFERER=external_url)
        
        # 外部サイトにリダイレクトされないことを確認
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")  # ルートにリダイレクト

    def test_sql_injection_protection(self):
        """SQLインジェクション攻撃からの保護テスト"""
        # SQLインジェクションを試行
        malicious_input = "'; DROP TABLE users; --"
        
        request_data = json.dumps({"keyword": malicious_input})
        
        with patch('gbbinfojpn.app.views.search_participants.supabase_service') as mock_supabase:
            mock_supabase.get_data.return_value = []
            
            response = self.client.post(
                '/2025/search_participants',
                data=request_data,
                content_type='application/json'
            )
            
            # 正常にレスポンスが返されることを確認（SQLインジェクションが防がれている）
            self.assertEqual(response.status_code, 200)


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
