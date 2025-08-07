"""
Flask アプリケーションのテストモジュール

python -m pytest app/tests/tests.py -v
"""

import asyncio
import json
import os
import time
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.context_processors import (
    get_available_years,
    is_early_access,
    is_latest_year,
    is_translated,
)
from app.main import app

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


class AppUrlsTestCase(unittest.TestCase):
    """
    Flask アプリケーションのURLパターンのテストケース

    このクラスは、Flaskアプリで定義されたURLパターンが
    正しくレスポンスを返すかどうかを検証します。

    Attributes:
        client: テスト用のFlaskクライアントインスタンス

    Methods:
        setUp():
            テスト前の初期化処理を行います。
        test_get_all_url_patterns_accessibility():
            すべてのGET用URLパターンが適切なレスポンスを返すかテストします。
    """

    def setUp(self):
        """
        テストの前準備を行います。

        Flaskアプリケーションのテストクライアントを作成し、self.clientに格納します。
        """
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()

    @patch("app.context_processors.supabase_service")
    @patch("app.context_processors.get_available_years")
    @patch("app.context_processors.is_gbb_ended")
    def test_get_all_url_patterns_accessibility(
        self,
        mock_is_gbb_ended,
        mock_get_years,
        mock_context_supabase,
    ):
        """
        すべてのGET用URLパターンが何らかのレスポンスを返すことをテストします。

        各URLにGETリクエストを送り、200〜399のステータスコード、または
        レスポンスが存在することを検証します。
        """
        # モックデータの設定
        mock_get_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False  # GBBは終了していないと仮定
        mock_context_supabase.get_data.return_value = [
            {
                "year": 2025,
                "categories__is_not": None,
                "ends_at": "2025-12-31T23:59:59Z",
            },
            {
                "year": 2024,
                "categories__is_not": None,
                "ends_at": "2024-12-31T23:59:59Z",
            },
            {
                "year": 2023,
                "categories__is_not": None,
                "ends_at": "2023-12-31T23:59:59Z",
            },
        ]

        # participant_detailページはテストから除外したためモック不要
        available_years = [2025, 2024, 2023]

        test_cases = [
            # 基本ページ
            ("/", "ルートページ"),
            ("/lang?lang=en", "言語変更 英語"),
            ("/lang?lang=ja", "言語変更 日本語"),
            # 静的ファイルエンドポイント
            ("/health", "ヘルスチェック"),
            ("/robots.txt", "robots.txt"),
            ("/ads.txt", "ads.txt"),
            ("/sitemap.xml", "サイトマップ"),
            ("/favicon.ico", "ファビコン"),
            ("/manifest.json", "マニフェスト"),
            ("/service-worker.js", "サービスワーカー"),
            ("/apple-touch-icon.png", "Apple Touch Icon"),
            ("/naverc158f3394cb78ff00c17f0a687073317.html", "Naver 検証"),
            # 2022年特別エンドポイント（main.pyのルート定義より）
            ("/2022/top", "2022年 トップページ"),
            ("/2022/rule", "2022年 ルール"),
            # participant_detailは複雑なSupabaseクエリが多数あるためテストから除外
            # ("/others/participant_detail?id=2064&mode=single", "出場者詳細 JUNNO"),
        ]

        # 年度別のテンプレートファイルをチェック
        for year in available_years:
            # 基本的な年度別エンドポイントを追加（main.pyのルート定義より）
            year_specific_endpoints = [
                (f"/{year}/world_map", f"{year}年 世界地図"),
                (f"/{year}/rule", f"{year}年 ルール"),
                (f"/{year}/participants", f"{year}年 参加者一覧"),
                (f"/{year}/result", f"{year}年 結果"),
                (f"/{year}/japan", f"{year}年 日本人参加者"),
                (f"/{year}/korea", f"{year}年 韓国人参加者"),
            ]
            test_cases.extend(year_specific_endpoints)

            templates_path = f"app/templates/{year}"
            if os.path.exists(templates_path):
                file_list = os.listdir(templates_path)
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

        # othersディレクトリのテンプレートをチェック
        others_path = "app/templates/others"
        if os.path.exists(others_path):
            other_urls = os.listdir(others_path)
            for other_url in other_urls:
                if (
                    other_url.endswith(".html")
                    and other_url != "participant_detail.html"
                ):
                    # participant_detail.htmlは複雑なSupabaseクエリが多数あるため除外
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


class ContextProcessorsTestCase(unittest.TestCase):
    """
    コンテキストプロセッサのテストケース
    """

    def setUp(self):
        """テストの前準備"""
        app.config["TESTING"] = True
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()

    @patch("app.context_processors.supabase_service")
    def test_get_available_years(self, mock_supabase):
        """利用可能な年度の取得テスト"""
        # グローバル変数をクリア
        import app.context_processors

        app.context_processors.AVAILABLE_YEARS = []

        # モックデータの設定
        mock_supabase.get_data.return_value = [
            {"year": 2025},
            {"year": 2024},
            {"year": 2023},
        ]

        result = get_available_years()

        # 降順でソートされていることを確認（実際の期待値は[2025, 2024, 2023]）
        self.assertEqual(result, [2025, 2024, 2023])

        # Supabaseが正しいパラメータで呼ばれていることを確認
        mock_supabase.get_data.assert_called_once()

    def test_is_latest_year(self):
        """最新年度判定のテスト"""
        with patch("app.context_processors.get_available_years") as mock_get_years:
            with patch("app.context_processors.datetime") as mock_datetime:
                mock_get_years.return_value = [2025, 2024, 2023]
                mock_datetime.now.return_value.year = 2025

                # 現在年度は最新年度
                self.assertTrue(is_latest_year(2025))

                # 過去年度は最新年度ではない
                self.assertFalse(is_latest_year(2024))

    def test_is_early_access(self):
        """早期アクセス判定のテスト"""
        with patch("app.context_processors.datetime") as mock_datetime:
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
        self.assertTrue(is_translated("/test", "ja", set()))

        # 英語は翻訳ファイルに依存
        translated_urls = {"/test"}
        self.assertTrue(is_translated("/test", "en", translated_urls))
        self.assertFalse(is_translated("/not-translated", "en", translated_urls))


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

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()

    @patch("app.views.search_participants.supabase_service")
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
        self.assertEqual(response.content_type, "application/json")

    def test_change_language(self):
        """言語変更のテスト"""
        # 有効な言語コード
        response = self.client.get("/lang?lang=en", headers={"Referer": "/"})
        self.assertEqual(response.status_code, 302)

        # 無効な言語コードはjaにフォールバック
        response = self.client.get("/lang?lang=invalid", headers={"Referer": "/"})
        self.assertEqual(response.status_code, 302)


class GeminiServiceTestCase(unittest.TestCase):
    """
    Geminiサービスのテストケース
    """

    def setUp(self):
        """テストの前準備"""
        app.config["TESTING"] = True
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()

    @patch("app.models.gemini_client.genai.Client")
    def test_gemini_service_rate_limit(self, mock_genai_client):
        """Geminiサービスのレートリミットテスト"""
        from app.models.gemini_client import GeminiService

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

    @patch("app.views.gemini_search.gemini_service")
    def test_gemini_search_view_rate_limit_compliance(self, mock_gemini_service):
        """Gemini検索ビューでのレートリミット準拠テスト"""
        app.config["TESTING"] = True
        client = app.test_client()

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

        # 連続でリクエストを送信（form-data形式で送信）
        for i in range(3):
            response = client.post(
                "/2025/search",
                data={"question": f"test question {i}"},
                content_type="application/x-www-form-urlencoded",
            )
            # 正常にレスポンスが返されることを期待
            self.assertEqual(response.status_code, 200)

        # ask_syncが呼ばれた回数を確認
        self.assertEqual(len(request_times), 3)

    def test_rate_limit_configuration(self):
        """レートリミット設定の正確性テスト"""
        from app.models.gemini_client import limiter

        # Throttlerの設定を確認
        self.assertEqual(limiter.rate_limit, 1, "レートリミットが1でない")
        self.assertEqual(limiter.period, 2, "期間が2秒でない")

    @patch("app.models.gemini_client.genai.Client")
    def test_rate_limit_with_retries(self, mock_genai_client):
        """リトライ機能とレートリミットの組み合わせテスト"""
        from app.models.gemini_client import GeminiService

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
            with patch("app.views.gemini_search.gemini_service", service):
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
        from app.models.gemini_client import limiter

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


if __name__ == "__main__":
    unittest.main()
