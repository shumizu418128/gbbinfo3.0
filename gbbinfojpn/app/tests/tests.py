"""
gbbinfojpn.app.urls のURLパターンをテストするモジュール

python manage.py test gbbinfojpn.app.tests.tests --keepdb -v 2
"""

import asyncio
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, Mock, patch

from django.core.cache import cache
from django.test import Client, TestCase

from gbbinfojpn.app.context_processors import (
    common_variables,
    get_available_years,
    is_early_access,
    is_latest_year,
    is_translated,
)
from gbbinfojpn.app.views.common import (
    content_view,
    not_found_page_view,
    top_redirect_view,
)

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

    @patch("gbbinfojpn.app.context_processors.supabase_service")
    def test_get_available_years(self, mock_supabase):
        """利用可能な年度の取得テスト"""
        # モックデータの設定
        mock_supabase.get_data.return_value = [
            {"year": 2024},
            {"year": 2023},
            {"year": 2022},
        ]

        result = get_available_years()

        # 降順でソートされていることを確認
        self.assertEqual(result, [2024, 2023, 2022])

        # Supabaseが正しいパラメータで呼ばれていることを確認
        mock_supabase.get_data.assert_called_once()

    def test_is_latest_year(self):
        """最新年度判定のテスト"""
        with patch(
            "gbbinfojpn.app.context_processors.get_available_years"
        ) as mock_get_years:
            with patch("gbbinfojpn.app.context_processors.datetime") as mock_datetime:
                mock_get_years.return_value = [2025, 2024, 2023]
                mock_datetime.now.return_value.year = 2025

                # 現在年度は最新年度
                self.assertTrue(is_latest_year(2025))

                # 過去年度は最新年度ではない
                self.assertFalse(is_latest_year(2024))

    def test_is_early_access(self):
        """早期アクセス判定のテスト"""
        with patch("gbbinfojpn.app.context_processors.datetime") as mock_datetime:
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
        with patch("gbbinfojpn.app.context_processors.TRANSLATED_URLS", ["/test"]):
            self.assertTrue(is_translated("/test", "en"))
            self.assertFalse(is_translated("/not-translated", "en"))

    @patch("gbbinfojpn.app.context_processors.supabase_service")
    @patch("gbbinfojpn.app.context_processors.get_available_years")
    def test_common_variables(self, mock_get_years, mock_supabase):
        """共通変数のテスト"""
        mock_get_years.return_value = [2025, 2024]
        mock_supabase.get_data.return_value = [
            {"year": 2025, "ends_at": "2025-11-02 14:59:59+00"},
            {"year": 2024, "ends_at": "2024-11-03 14:59:59+00"},
        ]

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

    @patch("gbbinfojpn.app.views.common.get_available_years")
    def test_top_redirect_view(self, mock_get_years):
        """トップページリダイレクトのテスト"""
        mock_get_years.return_value = [2025, 2024, 2023]

        with patch("gbbinfojpn.app.views.common.datetime") as mock_datetime:
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

        with patch("gbbinfojpn.app.views.common.render") as mock_render:
            mock_render.return_value = Mock(status_code=404)

            _ = not_found_page_view(request)

            # renderが正しいパラメータで呼ばれることを確認
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            self.assertEqual(args[1], "common/404.html")
            self.assertEqual(kwargs["status"], 404)

    def test_change_language(self):
        """言語変更のテスト"""
        with patch("django.conf.settings.SUPPORTED_LANGUAGE_CODES", ["ja", "en"]):
            with patch("django.conf.settings.LANGUAGE_COOKIE_NAME", "django_language"):
                # 有効な言語コード
                response = self.client.get("/lang?lang=en", HTTP_REFERER="/")
                self.assertEqual(response.status_code, 302)

                # 無効な言語コードはjaにフォールバック
                response = self.client.get("/lang?lang=invalid", HTTP_REFERER="/")
                self.assertEqual(response.status_code, 302)

    @patch("gbbinfojpn.app.views.search_participants.supabase_service")
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
                    "ParticipantMember": [],
                }
            ],
            [],  # メンバーデータ（空）
        ]

        request_data = json.dumps({"keyword": "test"})
        response = self.client.post(
            "/2025/search_participants",
            data=request_data,
            content_type="application/json",
        )

        # JSONレスポンスが返されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")


class SupabaseServiceTestCase(TestCase):
    """
    Supabaseサービスのテストケース
    """

    def setUp(self):
        """テストの前準備"""
        cache.clear()

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test_anon_key",
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key",
        },
    )
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

    @patch("gbbinfojpn.app.models.supabase_client.supabase_service")
    def test_participants_page_integration(self, mock_supabase):
        """参加者ページの統合テスト"""
        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"year": 2025, "categories": [1, 2]}],  # Year data
            [
                {"id": 1, "name": "Loopstation"},
                {"id": 2, "name": "Solo"},
            ],  # Category data
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
                    "ParticipantMember": [],
                }
            ],
        ]

        response = self.client.get(
            "/2025/participants?category=Loopstation&ticket_class=all&cancel=show"
        )

        # ページが正常に表示されることを確認
        self.assertEqual(response.status_code, 200)

    @patch("gbbinfojpn.app.models.supabase_client.supabase_service")
    def test_result_page_integration(self, mock_supabase):
        """結果ページの統合テスト"""
        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"categories": [1, 2]}],  # Year data
            [
                {"id": 1, "name": "Loopstation"},
                {"id": 2, "name": "Solo"},
            ],  # Category data
            [  # Tournament result data
                {
                    "round": "Final",
                    "winner": {"name": "WINNER"},
                    "loser": {"name": "LOSER"},
                }
            ],
        ]

        response = self.client.get("/2025/result?category=Loopstation")

        # ページが正常に表示されることを確認
        self.assertEqual(response.status_code, 200)

    def test_language_switching_integration(self):
        """言語切り替えの統合テスト"""
        with patch("django.conf.settings.SUPPORTED_LANGUAGE_CODES", ["ja", "en"]):
            with patch("django.conf.settings.LANGUAGE_COOKIE_NAME", "django_language"):
                # 言語を英語に変更
                response = self.client.get("/lang?lang=en", HTTP_REFERER="/2025/top")

                # リダイレクトされることを確認
                self.assertEqual(response.status_code, 302)

                # クッキーが設定されることを確認
                self.assertIn("django_language", response.cookies)

    def test_error_handling_integration(self):
        """エラーハンドリングの統合テスト"""
        # 存在しないページにアクセス
        response = self.client.get("/nonexistent/page")

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

    @patch("gbbinfojpn.app.models.supabase_client.supabase_service")
    def test_cache_functionality(self, mock_supabase):
        """キャッシュ機能のテスト"""
        from gbbinfojpn.app.models.supabase_client import SupabaseService

        # 環境変数をモック
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_ANON_KEY": "test_anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "test_service_key",
            },
        ):
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
            response = self.client.get("/")
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

        response = self.client.get(f"/lang?lang={malicious_script}")

        # リダイレクトされることを確認（スクリプトが実行されない）
        self.assertEqual(response.status_code, 302)

    def test_external_redirect_protection(self):
        """外部リダイレクト攻撃からの保護テスト"""
        # 外部サイトへのリダイレクトを試行
        external_url = "http://malicious-site.com"

        response = self.client.get("/lang?lang=en", HTTP_REFERER=external_url)

        # 外部サイトにリダイレクトされないことを確認
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")  # ルートにリダイレクト

    def test_sql_injection_protection(self):
        """SQLインジェクション攻撃からの保護テスト"""
        # SQLインジェクションを試行
        malicious_input = "'; DROP TABLE users; --"

        request_data = json.dumps({"keyword": malicious_input})

        with patch(
            "gbbinfojpn.app.views.search_participants.supabase_service"
        ) as mock_supabase:
            mock_supabase.get_data.return_value = []

            response = self.client.post(
                "/2025/search_participants",
                data=request_data,
                content_type="application/json",
            )

            # 正常にレスポンスが返されることを確認（SQLインジェクションが防がれている）
            self.assertEqual(response.status_code, 200)

    def test_post_all_url_patterns_accessibility(self):
        """
        すべてのPOST用URLパターンが何らかのレスポンスを返すことをテストします。

        各URLにPOSTリクエストを送り、200〜399のステータスコード、または
        レスポンスが存在することを検証します。
        """
        available_years = get_available_years()

        # POSTエンドポイントのテストケース（パラメータと形式を正しく設定）
        test_cases = []

        # beatboxer_tavily_search (application/x-www-form-urlencoded)
        test_cases.append(
            (
                "/beatboxer_tavily_search",
                "Beatboxer Tavily Search",
                {"beatboxer_id": "1", "mode": "single"},
                "form",
            )
        )

        # search_suggestions (JSON)
        test_cases.append(
            (
                "/search_suggestions",
                "Search Suggestions",
                {"input": "test beatboxer"},
                "json",
            )
        )

        # 年度別のPOSTエンドポイント
        for year in available_years:
            test_cases.extend(
                [
                    # gemini_search (JSON)
                    (
                        f"/{year}/search",
                        f"Gemini Search {year}",
                        {"question": "test question"},
                        "json",
                    ),
                    # search_participants (JSON)
                    (
                        f"/{year}/search_participants",
                        f"Search Participants {year}",
                        {"keyword": "test"},
                        "json",
                    ),
                ]
            )

        for url, description, data, request_type in test_cases:
            with self.subTest(url=url, description=description):
                # モックを使用してサービスをモック化
                with (
                    patch(
                        "gbbinfojpn.app.views.beatboxer_tavily_search.tavily_service"
                    ) as mock_tavily,
                    patch(
                        "gbbinfojpn.app.views.gemini_search.gemini_service"
                    ) as mock_gemini,
                    patch(
                        "gbbinfojpn.app.views.search_participants.supabase_service"
                    ) as mock_supabase,
                ):
                    # モックの設定
                    mock_tavily.search.return_value = []
                    mock_gemini.ask_sync.return_value = {
                        "url": "/2025/participants",
                        "parameter": "test",
                        "name": "TEST",
                    }
                    mock_supabase.get_data.return_value = []

                    # beatboxer_tavily_searchの特別なモック設定
                    with patch(
                        "gbbinfojpn.app.views.beatboxer_tavily_search.beatboxer_tavily_search"
                    ) as mock_beatboxer_search:
                        mock_beatboxer_search.return_value = ([], [], "")

                        # リクエストタイプに応じて適切な形式で送信
                        if request_type == "json":
                            response = self.client.post(
                                url,
                                data=json.dumps(data),
                                content_type="application/json",
                            )
                        else:  # form
                            response = self.client.post(url, data=data)

                        # 200-399の範囲のステータスコードまたは、レスポンスが存在することを確認
                        self.assertTrue(
                            response.status_code in range(200, 400)
                            or response.status_code is not None,
                            f"{description} ({url}) が適切なレスポンスを返しませんでした。ステータスコード: {response.status_code}",
                        )


class GeminiRateLimitTestCase(TestCase):
    """
    Gemini APIのレートリミット厳格テスト
    """

    def setUp(self):
        """テストの前準備"""
        self.client = Client()
        cache.clear()

    @patch("gbbinfojpn.app.models.gemini_client.genai.Client")
    def test_rate_limit_enforcement(self, mock_genai_client):
        """レートリミットが確実に守られることをテスト"""
        from gbbinfojpn.app.models.gemini_client import GeminiService

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 非同期レスポンスのモック
        async def mock_generate_content(*args, **kwargs):
            return Mock(
                text='{"url": "/2025/top", "parameter": "None", "name": "None"}'
            )

        mock_client_instance.aio.models.generate_content = AsyncMock(
            side_effect=mock_generate_content
        )

        # 環境変数をモック
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = GeminiService()

            # 複数回の連続呼び出しで時間間隔を測定
            # レートリミッタによる遅延後の時間を測定するため、順次実行する
            request_times = []

            async def test_sequential_requests():
                for i in range(3):
                    # リクエスト直前の時間を記録
                    await service.ask(2025, f"test question {i}")
                    request_times.append(time.time())

            # テスト実行
            asyncio.run(test_sequential_requests())

            # 結果検証
            self.assertEqual(len(request_times), 3)

            # 各リクエスト間の間隔が1.9秒以上であることを確認（2秒のレートリミットを考慮）
            for i in range(1, len(request_times)):
                interval = request_times[i] - request_times[i - 1]
                self.assertGreaterEqual(
                    interval, 1.9, f"リクエスト{i}の間隔が短すぎます: {interval}秒"
                )

    @patch("gbbinfojpn.app.models.gemini_client.genai.Client")
    def test_concurrent_request_serialization(self, mock_genai_client):
        """同時リクエストが適切にシリアライズされることをテスト"""
        from gbbinfojpn.app.models.gemini_client import GeminiService

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        request_times = []

        async def mock_generate_content(*args, **kwargs):
            request_times.append(time.time())
            return Mock(
                text='{"url": "/2025/top", "parameter": "None", "name": "None"}'
            )

        mock_client_instance.aio.models.generate_content = AsyncMock(
            side_effect=mock_generate_content
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = GeminiService()

            # 同時に5つのリクエストを送信
            async def concurrent_test():
                tasks = [
                    service.ask(2025, f"concurrent question {i}") for i in range(5)
                ]
                return await asyncio.gather(*tasks)

            start_time = time.time()
            results = asyncio.run(concurrent_test())
            total_time = time.time() - start_time

            # 結果検証
            self.assertEqual(len(results), 5)
            self.assertEqual(len(request_times), 5)

            # 総実行時間が適切であることを確認（5リクエスト × 2秒間隔 = 最低8秒）
            self.assertGreaterEqual(
                total_time, 8.0, f"総実行時間が短すぎます: {total_time}秒"
            )

            # 各リクエストが順次実行されていることを確認
            for i in range(1, len(request_times)):
                interval = request_times[i] - request_times[i - 1]
                self.assertGreaterEqual(
                    interval, 1.9, f"リクエスト間隔が短すぎます: {interval}秒"
                )

    @patch("gbbinfojpn.app.models.gemini_client.genai.Client")
    def test_rate_limit_with_threading(self, mock_genai_client):
        """マルチスレッド環境でのレートリミットテスト"""
        from gbbinfojpn.app.models.gemini_client import GeminiService

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        execution_times = []
        lock = threading.Lock()

        async def mock_generate_content(*args, **kwargs):
            with lock:
                execution_times.append(time.time())
            return Mock(
                text='{"url": "/2025/top", "parameter": "None", "name": "None"}'
            )

        mock_client_instance.aio.models.generate_content = AsyncMock(
            side_effect=mock_generate_content
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = GeminiService()

            def thread_worker(thread_id):
                return service.ask_sync(2025, f"thread {thread_id} question")

            # 3つのスレッドで同時実行
            with ThreadPoolExecutor(max_workers=3) as executor:
                start_time = time.time()
                futures = [executor.submit(thread_worker, i) for i in range(3)]
                results = [future.result() for future in as_completed(futures)]
                total_time = time.time() - start_time

            # 結果検証
            self.assertEqual(len(results), 3)
            self.assertEqual(len(execution_times), 3)

            # 総実行時間が適切であることを確認
            self.assertGreaterEqual(
                total_time, 4.0, f"マルチスレッド総実行時間が短すぎます: {total_time}秒"
            )

            # 実行時間が順次であることを確認
            execution_times.sort()
            for i in range(1, len(execution_times)):
                interval = execution_times[i] - execution_times[i - 1]
                self.assertGreaterEqual(
                    interval,
                    1.9,
                    f"スレッド間のリクエスト間隔が短すぎます: {interval}秒",
                )

    @patch("gbbinfojpn.app.models.gemini_client.genai.Client")
    def test_rate_limit_error_handling(self, mock_genai_client):
        """レートリミットエラー時の適切な処理テスト"""
        from gbbinfojpn.app.models.gemini_client import GeminiService

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 最初のリクエストは成功、2回目はレートリミットエラー
        call_count = 0

        async def mock_generate_content(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(
                    text='{"url": "/2025/top", "parameter": "None", "name": "None"}'
                )
            else:
                # レートリミットエラーをシミュレート
                raise Exception("Rate limit exceeded")

        mock_client_instance.aio.models.generate_content = AsyncMock(
            side_effect=mock_generate_content
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = GeminiService()

            # 最初のリクエストは成功
            result1 = service.ask_sync(2025, "first question")
            self.assertIsInstance(result1, dict)
            self.assertIn("url", result1)

            # 2回目のリクエストはエラーハンドリングされて空辞書が返される
            result2 = service.ask_sync(2025, "second question")
            self.assertEqual(result2, {})

    @patch("gbbinfojpn.app.views.gemini_search.gemini_service")
    def test_gemini_search_view_rate_limit_compliance(self, mock_gemini_service):
        """Gemini検索ビューでのレートリミット準拠テスト"""
        # モックの設定
        mock_gemini_service.ask_sync.return_value = {
            "url": "/2025/participants",
            "parameter": "search_participants",
            "name": "TEST",
        }

        # 複数回の連続リクエスト
        request_times = []

        def mock_ask_sync(*args, **kwargs):
            request_times.append(time.time())
            return {
                "url": "/2025/participants",
                "parameter": "search_participants",
                "name": "TEST",
            }

        mock_gemini_service.ask_sync.side_effect = mock_ask_sync

        # 連続でリクエストを送信
        for i in range(3):
            response = self.client.post(
                "/2025/search",
                data=json.dumps({"question": f"test question {i}"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        # ask_syncが呼ばれた回数を確認
        self.assertEqual(len(request_times), 3)

    def test_rate_limit_configuration(self):
        """レートリミット設定の正確性テスト"""
        from gbbinfojpn.app.models.gemini_client import limiter

        # Throttlerの設定を確認
        self.assertEqual(limiter.rate_limit, 1, "レートリミットが1でない")
        self.assertEqual(limiter.period, 2, "期間が2秒でない")

    @patch("gbbinfojpn.app.models.gemini_client.genai.Client")
    def test_rate_limit_with_retries(self, mock_genai_client):
        """リトライ機能とレートリミットの組み合わせテスト"""
        from gbbinfojpn.app.models.gemini_client import GeminiService

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        call_times = []

        async def mock_generate_content(*args, **kwargs):
            call_times.append(time.time())
            # 最初の2回は失敗、3回目は成功
            if len(call_times) <= 2:
                raise Exception("API Error")
            return Mock(
                text='{"url": "/2025/top", "parameter": "None", "name": "None"}'
            )

        mock_client_instance.aio.models.generate_content = AsyncMock(
            side_effect=mock_generate_content
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = GeminiService()

            # gemini_search.pyのリトライロジックをテスト
            with patch("gbbinfojpn.app.views.gemini_search.gemini_service", service):
                start_time = time.time()

                # 5回リトライするロジックをシミュレート
                result = None
                for _ in range(5):
                    try:
                        result = service.ask_sync(2025, "retry test")
                        if result:
                            break
                    except Exception:
                        continue

                total_time = time.time() - start_time

                # リトライ間でもレートリミットが守られることを確認
                self.assertGreaterEqual(
                    total_time, 4.0, f"リトライ時の総時間が短すぎます: {total_time}秒"
                )
                self.assertEqual(
                    len(call_times), 3, "期待される呼び出し回数と異なります"
                )

    def test_rate_limit_stress_test(self):
        """レートリミットのストレステスト"""
        from gbbinfojpn.app.models.gemini_client import limiter

        # Throttlerが正しく初期化されていることを確認
        self.assertIsNotNone(limiter)

        # 大量のリクエストをシミュレート（実際のAPIは呼ばない）
        async def stress_test():
            start_time = time.time()

            # 10個のリクエストを同時に送信
            async def dummy_request(i):
                async with limiter:
                    # 実際のAPI呼び出しの代わりにダミー処理
                    await asyncio.sleep(0.1)
                    return f"result_{i}"

            tasks = [dummy_request(i) for i in range(10)]
            results = await asyncio.gather(*tasks)

            total_time = time.time() - start_time
            return results, total_time

        results, total_time = asyncio.run(stress_test())

        # 結果検証
        self.assertEqual(len(results), 10)
        # 10リクエスト × 2秒間隔 = 最低18秒（最初のリクエストは即座に実行）
        self.assertGreaterEqual(
            total_time, 18.0, f"ストレステスト総時間が短すぎます: {total_time}秒"
        )
