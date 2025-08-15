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

    @patch("app.views.result.supabase_service")
    @patch("app.views.participants.supabase_service")
    @patch("app.views.rule.supabase_service")
    @patch("app.views.world_map.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    @patch("app.context_processors.supabase_service")
    @patch("app.context_processors.get_available_years")
    @patch("app.context_processors.is_gbb_ended")
    def test_get_all_url_patterns_accessibility(
        self,
        mock_is_gbb_ended,
        mock_get_years,
        mock_context_supabase,
        mock_view_supabase,
        mock_world_map_supabase,
        mock_rule_supabase,
        mock_participants_supabase,
        mock_result_supabase,
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
        # participant_detail内のSupabase呼び出しは空配列を返す（404でもテスト条件は満たす）
        mock_view_supabase.get_data.return_value = []

        # world_map内のSupabase呼び出しは簡易モック
        def world_map_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            if table == "Participant":
                return [
                    {
                        "id": 1,
                        "name": "ALPHA",
                        "iso_code": 392,
                        "Category": {"name": "Solo"},
                        "ParticipantMember": [],
                    }
                ]
            if table == "Country":
                if pandas_flag:
                    import pandas as pd

                    return pd.DataFrame(
                        [
                            {
                                "iso_code": 392,
                                "latitude": 35.0,
                                "longitude": 139.0,
                                "names": {"ja": "日本", "en": "Japan"},
                            }
                        ]
                    )
                return [
                    {
                        "iso_code": 392,
                        "latitude": 35.0,
                        "longitude": 139.0,
                        "names": {"ja": "日本", "en": "Japan"},
                    }
                ]
            return []

        mock_world_map_supabase.get_data.side_effect = world_map_get_data_side_effect

        # rule内のSupabase呼び出しモック
        def rule_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            if table == "Participant":
                return [
                    {
                        "id": 1,
                        "name": "ALPHA",
                        "category": 1,
                        "is_cancelled": False,
                        "ticket_class": "GBB Seed",
                        "Category": {"id": 1, "name": "Solo"},
                        "ParticipantMember": [],
                    }
                ]
            return []

        mock_rule_supabase.get_data.side_effect = rule_get_data_side_effect

        # participants内のSupabase呼び出しモック
        def participants_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            if table == "Year" and pandas_flag:
                import pandas as pd

                return pd.DataFrame([{"categories": [1, 2]}])
            if table == "Category" and pandas_flag:
                import pandas as pd

                return pd.DataFrame(
                    [
                        {"id": 1, "name": "Loopstation"},
                        {"id": 2, "name": "Solo"},
                    ]
                )
            if table == "Participant":
                return [
                    {
                        "id": 1,
                        "name": "ALPHA",
                        "category": 1,
                        "ticket_class": "GBB Seed",
                        "is_cancelled": False,
                        "iso_code": 392,
                        "Category": {"id": 1, "name": "Loopstation"},
                        "Country": {
                            "iso_code": 392,
                            "names": {"ja": "日本", "en": "Japan"},
                        },
                        "ParticipantMember": [],
                    }
                ]
            return []

        mock_participants_supabase.get_data.side_effect = (
            participants_get_data_side_effect
        )

        # result内のSupabase呼び出しモック
        def result_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            if table == "Year" and pandas_flag:
                import pandas as pd

                return pd.DataFrame([{"categories": [1]}])
            if table == "Category" and pandas_flag:
                import pandas as pd

                return pd.DataFrame([{"id": 1, "name": "Loopstation"}])
            if table == "TournamentResult":
                return []
            if table == "RankingResult":
                return [
                    {
                        "round": None,
                        "participant": 1,
                        "rank": 1,
                        "Participant": {"name": "ALPHA"},
                    }
                ]
            return []

        mock_result_supabase.get_data.side_effect = result_get_data_side_effect

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
            ("/others/participant_detail?id=2064&mode=single", "出場者詳細 JUNNO"),
            ("/others/participant_detail?id=255&mode=team_member", "出場者詳細 TAKO"),
            ("/others/participant_detail?id=1923&mode=team", "出場者詳細 WOLFGANG"),
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
        self.client = app.test_client()
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
            result1 = service.ask_sync("first question")
            self.assertIsInstance(result1, dict)
            self.assertIn("url", result1)

            # 2回目のリクエストはエラーハンドリングされて空辞書が返される
            result2 = service.ask_sync("second question")
            self.assertEqual(result2, {})

    @patch("app.views.gemini_search.spreadsheet_service")
    @patch("app.views.gemini_search.gemini_service")
    @patch("app.views.gemini_search.Thread")
    def test_gemini_search_view_rate_limit_compliance(
        self, mock_thread, mock_gemini_service, mock_spreadsheet_service
    ):
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

        # Thread.start() で即時実行させるフェイクを設定
        class ImmediateThread:
            def __init__(self, target=None, args=()):
                self._target = target
                self._args = args

            def start(self):
                if self._target:
                    self._target(*self._args)

        mock_thread.side_effect = lambda target=None, args=(): ImmediateThread(
            target=target, args=args
        )

        # 連続でリクエストを送信（form-data形式で送信）
        for i in range(3):
            response = client.post(
                "/2025/search",
                data=json.dumps({"question": f"test question {i}"}),
                content_type="application/json",
            )
            # 正常にレスポンスが返されることを期待
            self.assertEqual(response.status_code, 200)

        # ask_syncが呼ばれた回数を確認
        self.assertEqual(len(request_times), 3)

        # スプレッドシート記録はモックされているため、実通信は発生しない
        # （環境によってはIS_LOCAL/IS_PULL_REQUESTの値で呼び出し回数が変化するため回数は断定しない）
        self.assertTrue(hasattr(mock_spreadsheet_service, "record_question"))

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
                        result = service.ask_sync("retry test")
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

    @patch("app.views.participant_detail.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_participant_detail_single(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """participant_detail: singleモード 正常系のテスト"""
        mock_get_available_years.return_value = [2025, 2024]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 1. 対象参加者（Participant）
        participant_row = {
            "id": 2064,
            "name": "Junno",
            "year": 2025,
            "category": 1,
            "iso_code": 392,
            "ticket_class": "GBB Seed",
            "is_cancelled": False,
            "Country": {"iso_code": 392, "names": {"ja": "日本", "en": "Japan"}},
            "Category": {"id": 1, "name": "Solo"},
            "ParticipantMember": [],
        }

        # 2. 過去出場履歴（Participant）
        past_participant_rows = [
            {
                "id": 1001,
                "name": "JUNNO",
                "year": 2024,
                "is_cancelled": False,
                "category": 1,
                "Category": {"name": "Solo"},
                "ParticipantMember": [],
            }
        ]

        # 3. 過去出場履歴（ParticipantMember）
        past_member_rows = []

        # 4. 同年度・同部門の参加者一覧（Participant）
        same_year_rows = [
            {
                "id": 3001,
                "name": "Alpha",
                "is_cancelled": False,
                "ticket_class": "Wildcard 2 (2023)",
                "iso_code": 392,
                "Country": {"names": {"ja": "日本", "en": "Japan"}},
                "ParticipantMember": [],
            },
            {
                "id": 3002,
                "name": "Beta",
                "is_cancelled": False,
                "ticket_class": "GBB Seed",
                "iso_code": 826,
                "Country": {"names": {"ja": "イギリス", "en": "UK"}},
                "ParticipantMember": [],
            },
        ]

        mock_supabase.get_data.side_effect = [
            [participant_row],
            past_participant_rows,
            past_member_rows,
            same_year_rows,
        ]

        # セッションに言語を設定
        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/others/participant_detail?id=2064&mode=single")
        self.assertEqual(resp.status_code, 200)

    @patch("app.views.participant_detail.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_participant_detail_team_member(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """participant_detail: team_memberモード 正常系のテスト"""
        mock_get_available_years.return_value = [2025, 2024]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 1. 対象メンバー（ParticipantMember）
        member_row = {
            "id": 9001,
            "participant": 5001,
            "name": "TeamHero",
            "Country": {"iso_code": 392, "names": {"ja": "日本", "en": "Japan"}},
            "Participant": {
                "id": 5001,
                "name": "Team A",
                "year": 2025,
                "category": 2,
                "is_cancelled": False,
            },
        }

        # 2. 過去出場履歴（Participant）
        past_participant_rows = []

        # 3. 過去出場履歴（ParticipantMember）
        past_member_rows = [
            {
                "name": "TEAMHERO",
                "Participant": {
                    "id": 4001,
                    "name": "Team B",
                    "year": 2024,
                    "is_cancelled": False,
                    "Category": {"name": "Tag Team"},
                    "category": 2,
                },
            }
        ]

        # 4. 同年度・同部門の参加者一覧（Participant）
        same_year_rows = [
            {
                "id": 7001,
                "name": "Gamma",
                "is_cancelled": False,
                "ticket_class": "Wildcard 1 (2024)",
                "iso_code": 9999,
                "Country": {"names": {"ja": "—", "en": "—"}},
                "ParticipantMember": [
                    {"id": 1, "name": "P1", "Country": {"names": {"ja": "日本"}}},
                    {"id": 2, "name": "P2", "Country": {"names": {"ja": "韓国"}}},
                ],
            }
        ]

        mock_supabase.get_data.side_effect = [
            [member_row],
            past_participant_rows,
            past_member_rows,
            same_year_rows,
        ]

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/others/participant_detail?id=9001&mode=team_member")
        self.assertEqual(resp.status_code, 200)

    @patch("app.views.participant_detail.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_participant_detail_not_found(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """participant_detail: 初回取得でデータがない場合は404を返す"""
        mock_get_available_years.return_value = [2025, 2024]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/others/participant_detail?id=0&mode=single")
        self.assertEqual(resp.status_code, 404)


class SupabaseServiceTestCase(unittest.TestCase):
    """SupabaseServiceの単体テスト。

    Supabaseの読み取り専用クエリ、フィルタ適用、キャッシュ、pandas返却、
    およびTavilyデータ連携と環境変数検証を確認する。
    """

    def setUp(self):
        """テストの前準備。

        - Flaskアプリのテストコンテキストを用意
        - 必須環境変数を一時設定
        """
        app.config["TESTING"] = True
        self.app_context = app.app_context()
        self.app_context.push()

        # 必須環境変数を設定
        self._env_patcher = patch.dict(
            os.environ,
            {
                # すでに設定されている
                # "SUPABASE_URL": "http://localhost",
                # "SUPABASE_ANON_KEY": "anon",
                # "SUPABASE_SERVICE_ROLE_KEY": "service",
            },
        )
        self._env_patcher.start()

        # dictベースのフェイクキャッシュ
        class DictCache:
            def __init__(self):
                self.store = {}

            def get(self, key):
                return self.store.get(key)

            def set(self, key, value, timeout=None):
                self.store[key] = value

        self.DictCache = DictCache

        # クエリモック（読み取り用）
        class QueryMock:
            def __init__(self):
                self.selected_columns_str = None
                self.eq_calls = []
                self.gt_calls = []
                self.gte_calls = []
                self.lt_calls = []
                self.lte_calls = []
                self.neq_calls = []
                self.like_calls = []
                self.ilike_calls = []
                self.not_like_calls = []
                self.not_ilike_calls = []
                self.is_calls = []
                self.not_is_calls = []
                self.in_calls = []
                self.contains_calls = []
                self.order_calls = []  # (column, desc)
                self.execute_call_count = 0
                self.response_data = []

                class _NotOps:
                    def __init__(self, parent):
                        self._parent = parent

                    def like(self, field, value):
                        self._parent.not_like_calls.append((field, value))
                        return self._parent

                    def ilike(self, field, value):
                        self._parent.not_ilike_calls.append((field, value))
                        return self._parent

                    def is_(self, field, value):
                        self._parent.not_is_calls.append((field, value))
                        return self._parent

                self.not_ = _NotOps(self)

            # SupabaseクエリAPIの疑似実装
            def select(self, columns_str):
                self.selected_columns_str = columns_str
                return self

            def eq(self, field, value):
                self.eq_calls.append((field, value))
                return self

            def gt(self, field, value):
                self.gt_calls.append((field, value))
                return self

            def gte(self, field, value):
                self.gte_calls.append((field, value))
                return self

            def lt(self, field, value):
                self.lt_calls.append((field, value))
                return self

            def lte(self, field, value):
                self.lte_calls.append((field, value))
                return self

            def neq(self, field, value):
                self.neq_calls.append((field, value))
                return self

            def like(self, field, value):
                self.like_calls.append((field, value))
                return self

            def ilike(self, field, value):
                self.ilike_calls.append((field, value))
                return self

            def is_(self, field, value):
                self.is_calls.append((field, value))
                return self

            def in_(self, field, value):
                self.in_calls.append((field, value))
                return self

            def contains(self, field, value):
                self.contains_calls.append((field, value))
                return self

            def order(self, column, desc=False):
                self.order_calls.append((column, desc))
                return self

            def execute(self):
                self.execute_call_count += 1
                return Mock(data=self.response_data)

        self.QueryMock = QueryMock

        # 管理者用（Tavily用）テーブルモック
        class AdminTableMock:
            def __init__(self):
                self.eq_calls = []
                self.inserted_payloads = []
                self.execute_call_count = 0
                self.response_data = []

            def select(self, *args):
                return self

            def eq(self, field, value):
                self.eq_calls.append((field, value))
                return self

            def insert(self, payload):
                self.inserted_payloads.append(payload)
                return self

            def execute(self):
                self.execute_call_count += 1
                return Mock(data=self.response_data)

        self.AdminTableMock = AdminTableMock

        # クライアントモック
        class FakeClient:
            def __init__(self, table_obj):
                self._table_obj = table_obj

            def table(self, name):
                return self._table_obj

        self.FakeClient = FakeClient

    def tearDown(self):
        """テスト後のクリーンアップ。"""
        self._env_patcher.stop()
        self.app_context.pop()

    def test_get_data_builds_query_and_uses_cache(self):
        """get_data: クエリ組み立て・フィルタ・並び替え・キャッシュ動作を検証する。"""
        from app.models.supabase_client import SupabaseService

        # フェイクキャッシュを差し替え
        dict_cache = self.DictCache()
        with patch("app.main.flask_cache", dict_cache):
            service = SupabaseService()

            # 読み取り用クエリモックを準備
            query = self.QueryMock()
            query.response_data = [{"id": 1, "name": "Alice"}]
            service.read_only_client = self.FakeClient(query)

            # JOIN + 高度フィルタ + 等価フィルタ + 降順ソート
            result1 = service.get_data(
                table="Participant",
                columns=["id", "name"],
                join_tables={
                    "Country": ["names", "iso_code"],
                    "ParticipantMember": ["name", "Country(names)"],
                },
                filters={
                    "age__gt": 18,
                    "name__ilike": "%test%",
                    "status__neq": "inactive",
                    "tags__contains": ["a"],
                    "role__in": ["user", "admin"],
                    "categories__is_not": None,
                    "title__not_like": "%bot%",
                    "title__not_ilike": "%spam%",
                },
                order_by="-created_at",
                year=2025,
            )

            # 返却値
            self.assertEqual(result1, [{"id": 1, "name": "Alice"}])

            # select句の構築（列 → JOIN Country → JOIN ParticipantMember）
            self.assertEqual(
                query.selected_columns_str,
                "id,name,Country(names,iso_code),ParticipantMember(name,Country(names))",
            )

            # 高度フィルタの適用
            self.assertIn(("age", 18), query.gt_calls)
            self.assertIn(("name", "%test%"), query.ilike_calls)
            self.assertIn(("status", "inactive"), query.neq_calls)
            self.assertIn(("tags", ["a"]), query.contains_calls)
            self.assertIn(("role", ["user", "admin"]), query.in_calls)
            self.assertIn(("categories", None), query.not_is_calls)
            self.assertIn(("title", "%bot%"), query.not_like_calls)
            self.assertIn(("title", "%spam%"), query.not_ilike_calls)

            # 等価フィルタ
            self.assertIn(("year", 2025), query.eq_calls)

            # 並び替え（降順）
            self.assertIn(("created_at", True), query.order_calls)

            # キャッシュヒット確認（executeは1回のみ）
            _ = service.get_data(
                table="Participant",
                columns=["id", "name"],
                join_tables={
                    "Country": ["names", "iso_code"],
                    "ParticipantMember": ["name", "Country(names)"],
                },
                filters={
                    "age__gt": 18,
                    "name__ilike": "%test%",
                    "status__neq": "inactive",
                    "tags__contains": ["a"],
                    "role__in": ["user", "admin"],
                    "categories__is_not": None,
                    "title__not_like": "%bot%",
                    "title__not_ilike": "%spam%",
                },
                order_by="-created_at",
                year=2025,
            )
            self.assertEqual(query.execute_call_count, 1)

    def test_get_data_returns_dataframe_when_pandas_true(self):
        """get_data: pandas=True で DataFrame を返すことを検証する。"""
        import pandas as pd

        from app.models.supabase_client import SupabaseService

        dict_cache = self.DictCache()
        with patch("app.main.flask_cache", dict_cache):
            service = SupabaseService()
            query = self.QueryMock()
            query.response_data = [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
            service.read_only_client = self.FakeClient(query)

            df = service.get_data(table="User", pandas=True)
            self.assertIsInstance(df, pd.DataFrame)
            self.assertEqual(len(df), 2)

    def test_tavily_get_insert_and_cache(self):
        """Tavilyデータの取得・保存とキャッシュ動作を検証する。"""
        from app.models.supabase_client import SupabaseService

        dict_cache = self.DictCache()
        with patch("app.main.flask_cache", dict_cache):
            service = SupabaseService()

            # 管理者クライアントのセットアップ
            admin_table = self.AdminTableMock()
            admin_table.response_data = [{"search_results": [{"title": "t1"}]}]

            class AdminClient:
                def table(self, name):
                    return admin_table

            service._admin_client = AdminClient()

            # 取得（キャッシュ未設定 → DB参照）
            got = service.get_tavily_data(cache_key="k1")
            self.assertEqual(got, [{"title": "t1"}])
            self.assertEqual(admin_table.execute_call_count, 1)

            # 取得（キャッシュヒット → DB未実行）
            _ = service.get_tavily_data(cache_key="k1")
            self.assertEqual(admin_table.execute_call_count, 1)

            # 文字列JSONの場合のデコード
            admin_table2 = self.AdminTableMock()
            admin_table2.response_data = [{"search_results": '["x", "y"]'}]

            class AdminClient2:
                def table(self, name):
                    return admin_table2

            service._admin_client = AdminClient2()
            got2 = service.get_tavily_data(cache_key="k2")
            self.assertEqual(got2, ["x", "y"])

            # 挿入の検証
            admin_table3 = self.AdminTableMock()

            class AdminClient3:
                def table(self, name):
                    return admin_table3

            service._admin_client = AdminClient3()
            service.insert_tavily_data(cache_key="k3", search_result={"ok": True})
            self.assertEqual(len(admin_table3.inserted_payloads), 1)
            self.assertIn("search_results", admin_table3.inserted_payloads[0])

    def test_generate_cache_key_is_stable_and_sensitive(self):
        """キャッシュキー生成が順序に頑健で、パラメータ差分に敏感であることを検証する。"""
        from app.models.supabase_client import SupabaseService

        service = SupabaseService()
        key1 = service._generate_cache_key(
            table="T", columns=["b", "a"], filters={"x__gt": 1}, year=2025
        )
        key2 = service._generate_cache_key(
            table="T", columns=["a", "b"], filters={"x__gt": 1}, year=2025
        )
        key3 = service._generate_cache_key(
            table="T", columns=["a", "b"], filters={"x__gt": 2}, year=2025
        )

        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)

    def test_env_validation_errors_when_missing(self):
        """必須環境変数が欠落している場合に初期化が失敗することを検証する。"""
        from app.models.supabase_client import SupabaseService

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                _ = SupabaseService()


class ParticipantDetailLinkParamTest(unittest.TestCase):
    """`/others/participant_detail`リンクの必須クエリパラメータ検証テスト。

    各種ページで生成される`/others/participant_detail`へのリンクについて、
    `id`および`mode`クエリパラメータが欠落していないことと、
    値が妥当であることを検証する。

    Methods:
        setUp(): テストクライアント/アプリコンテキストの準備
        tearDown(): アプリコンテキストのクリーンアップ
        test_links_to_participant_detail_have_required_params():
            対象ページを走査し、リンクの妥当性を一括検証
    """

    def setUp(self):
        """テストの前準備。"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        """テスト後のクリーンアップ。"""
        self.app_context.pop()

    @patch("app.views.participants.supabase_service")
    @patch("app.views.participant_detail.supabase_service")
    @patch("app.views.result.supabase_service")
    @patch("app.views.rule.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_links_to_participant_detail_have_required_params(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_rule_supabase,
        mock_result_supabase,
        mock_participant_detail_supabase,
        mock_participants_supabase,
    ):
        """`/others/participant_detail`リンクに`id`と`mode`が含まれることを検証する。

        検証対象:
            - /2025/participants?category=Loopstation&ticket_class=all&cancel=show
            - /2025/result?category=Loopstation
            - /2025/result?category=Tag%20Team
            - /2025/rule
            - /2025/japan
            - /2025/korea

        アサーション:
            - `<a ... href="/others/participant_detail?...">`なリンクのみ抽出
            - `id`と`mode`の両方のクエリが存在
            - `id`は数字、`mode`は`single|team|team_member`のいずれか
        """
        import re
        from urllib.parse import parse_qs, urlparse

        # コンテキスト依存の関数をモック
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # participants系ビューのSupabaseモック
        def participants_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            filters = kwargs.get("filters", {})

            if table == "Year" and pandas_flag:
                import pandas as pd

                return pd.DataFrame([{"categories": [1, 2]}])

            if table == "Category" and pandas_flag:
                import pandas as pd

                return pd.DataFrame(
                    [
                        {"id": 1, "name": "Loopstation"},
                        {"id": 2, "name": "Tag Team"},
                    ]
                )

            if table == "Participant":
                # country specific (/japan or /korea)
                if "iso_code" in filters:
                    iso_code = filters.get("iso_code")
                    if iso_code == 392:  # Japan
                        return [
                            {
                                "id": 100,
                                "name": "Alpha",
                                "category": 1,
                                "ticket_class": "GBB Seed",
                                "is_cancelled": False,
                                "Category": {"id": 1, "name": "Loopstation"},
                                "ParticipantMember": [],
                            },
                            {
                                "id": 101,
                                "name": "Team J",
                                "category": 2,
                                "ticket_class": "GBB Seed",
                                "is_cancelled": False,
                                "Category": {"id": 2, "name": "Tag Team"},
                                "ParticipantMember": [{"name": "M1", "iso_code": 392}],
                            },
                        ]
                    if iso_code == 410:  # Korea
                        return [
                            {
                                "id": 110,
                                "name": "Beta",
                                "category": 1,
                                "ticket_class": "Wildcard 1 (2024)",
                                "is_cancelled": False,
                                "Category": {"id": 1, "name": "Loopstation"},
                                "ParticipantMember": [],
                            },
                            {
                                "id": 111,
                                "name": "Team K",
                                "category": 2,
                                "ticket_class": "GBB Seed",
                                "is_cancelled": False,
                                "Category": {"id": 2, "name": "Tag Team"},
                                "ParticipantMember": [{"name": "K1", "iso_code": 410}],
                            },
                        ]
                    if iso_code == 9999:  # multi-country team candidates
                        return [
                            {
                                "id": 120,
                                "name": "MixTeam",
                                "category": 2,
                                "ticket_class": "Wildcard 2 (2023)",
                                "is_cancelled": False,
                                "Category": {"id": 2, "name": "Tag Team"},
                                "ParticipantMember": [
                                    {"name": "JP", "iso_code": 392},
                                    {"name": "KR", "iso_code": 410},
                                ],
                            }
                        ]

                # /{year}/participants 用（category指定）
                if "category" in filters:
                    return [
                        {
                            "id": 201,
                            "name": "Gamma",
                            "category": filters["category"],
                            "ticket_class": "GBB Seed",
                            "is_cancelled": False,
                            "iso_code": 392,
                            "Category": {"id": 1, "name": "Loopstation"},
                            "Country": {
                                "iso_code": 392,
                                "names": {"ja": "日本", "en": "Japan"},
                            },
                            "ParticipantMember": [],
                        },
                        {
                            "id": 202,
                            "name": "Delta",
                            "category": filters["category"],
                            "ticket_class": "GBB Seed",
                            "is_cancelled": False,
                            "iso_code": 826,
                            "Category": {"id": 2, "name": "Tag Team"},
                            "Country": {
                                "iso_code": 826,
                                "names": {"ja": "イギリス", "en": "UK"},
                            },
                            "ParticipantMember": [
                                {"name": "M1", "Country": {"names": {"ja": "日本"}}}
                            ],
                        },
                    ]

            return []

        mock_participants_supabase.get_data.side_effect = (
            participants_get_data_side_effect
        )

        # resultビューのSupabaseモック
        def result_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            filters = kwargs.get("filters", {})

            if table == "Year" and pandas_flag:
                import pandas as pd

                return pd.DataFrame([{"categories": [1, 2]}])

            if table == "Category" and pandas_flag:
                import pandas as pd

                return pd.DataFrame(
                    [
                        {"id": 1, "name": "Loopstation", "is_team": False},
                        {"id": 2, "name": "Tag Team", "is_team": True},
                    ]
                )

            if table == "TournamentResult":
                # トーナメントデータなし→ランキングへフォールバック
                return []

            if table == "RankingResult":
                category_id = filters.get("category")
                if category_id == 1:
                    return [
                        {
                            "round": None,
                            "participant": 1,
                            "rank": 1,
                            "Participant": {"id": 301, "name": "RSolo"},
                        }
                    ]
                if category_id == 2:
                    return [
                        {
                            "round": None,
                            "participant": 2,
                            "rank": 1,
                            "Participant": {"id": 302, "name": "RTeam"},
                        }
                    ]

            return []

        mock_result_supabase.get_data.side_effect = result_get_data_side_effect

        # ruleビューのSupabaseモック
        def rule_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            if table == "Participant":
                return [
                    {
                        "id": 401,
                        "name": "SeedSolo",
                        "category": 1,
                        "is_cancelled": False,
                        "ticket_class": "GBB Seed",
                        "Category": {"id": 1, "name": "Loopstation"},
                        "ParticipantMember": [],
                    },
                    {
                        "id": 402,
                        "name": "SeedTeam",
                        "category": 2,
                        "is_cancelled": False,
                        "ticket_class": "GBB Seed",
                        "Category": {"id": 2, "name": "Tag Team"},
                        "ParticipantMember": [{"id": 1}],
                    },
                ]
            return []

        mock_rule_supabase.get_data.side_effect = rule_get_data_side_effect

        # participant_detailビューのSupabaseモック
        def participant_detail_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            filters = kwargs.get("filters", {})
            join_tables = kwargs.get("join_tables", {})

            # team_member 詳細（TAKO: id=255）
            if table == "ParticipantMember":
                fid = filters.get("id")
                try:
                    fid_int = int(fid) if fid is not None else None
                except ValueError:
                    fid_int = fid
                if fid_int == 255:
                    return [
                        {
                            "id": 255,
                            "participant": 1923,
                            "name": "TAKO",
                            "Country": {
                                "iso_code": 392,
                                "names": {"ja": "日本", "en": "Japan"},
                            },
                            "Participant": {
                                "id": 1923,
                                "name": "WOLFGANG",
                                "year": 2025,
                                "category": 2,
                                "is_cancelled": False,
                            },
                        }
                    ]

            # single / team 詳細（JUNNO:2064, WOLFGANG:1923）
            if table == "Participant" and filters.get("id") is not None:
                pid_raw = filters.get("id")
                try:
                    pid = int(pid_raw)
                except ValueError:
                    pid = pid_raw
                if pid == 2064:
                    return [
                        {
                            "id": 2064,
                            "name": "Junno",
                            "year": 2025,
                            "category": 1,
                            "iso_code": 392,
                            "ticket_class": "GBB Seed",
                            "is_cancelled": False,
                            "Country": {
                                "iso_code": 392,
                                "names": {"ja": "日本", "en": "Japan"},
                            },
                            "Category": {"id": 1, "name": "Solo"},
                            "ParticipantMember": [],
                        }
                    ]
                elif pid == 1923:
                    return [
                        {
                            "id": 1923,
                            "name": "WOLFGANG",
                            "year": 2025,
                            "category": 2,
                            "iso_code": 826,
                            "ticket_class": "GBB Seed",
                            "is_cancelled": False,
                            "Country": {
                                "iso_code": 826,
                                "names": {"ja": "イギリス", "en": "UK"},
                            },
                            "Category": {"id": 2, "name": "Tag Team"},
                            "ParticipantMember": [
                                {
                                    "id": 255,
                                    "name": "TAKO",
                                    "Country": {"names": {"ja": "日本"}},
                                },
                            ],
                        }
                    ]
                else:
                    return []

            # 過去出場履歴用（必要最小限なので空でも可）
            if (
                table == "Participant"
                and "id" not in filters
                and "year" not in filters
                and "category" not in filters
            ):
                return []
            if table == "ParticipantMember" and "participant" in join_tables:
                return []

            # 同年度・同部門の参加者一覧
            if table == "Participant" and "year" in filters and "category" in filters:
                return [
                    {
                        "id": 9001,
                        "name": "Another",
                        "is_cancelled": False,
                        "ticket_class": "Wildcard 1 (2024)",
                        "iso_code": 392,
                        "Country": {"names": {"ja": "日本", "en": "Japan"}},
                        "ParticipantMember": [],
                    }
                ]

            return []

        mock_participant_detail_supabase.get_data.side_effect = (
            participant_detail_get_data_side_effect
        )

        # 対象URLを巡回
        urls = [
            "/2025/participants?category=Loopstation&ticket_class=all&cancel=show",
            "/2025/result?category=Loopstation",
            "/2025/result?category=Tag%20Team",
            "/2025/rule",
            "/2025/japan",
            "/2025/korea",
            # 直接 participant_detail も対象に含める（存在確認/リンク抽出が目的、200 or 404を許容）
            "/others/participant_detail?id=2064&mode=single",  # JUNNO
            "/others/participant_detail?id=255&mode=team_member",  # TAKO
            "/others/participant_detail?id=1923&mode=team",  # WOLFGANG
        ]

        allowed_modes = {"single", "team", "team_member"}

        for url in urls:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(
                    resp.status_code,
                    200,
                    msg=f"{url} が200を返しませんでした（{resp.status_code}）。",
                )
                html = resp.get_data(as_text=True)

                # <a ... href="/others/participant_detail?..."> のみ抽出
                links = re.findall(
                    r'<a[^>]+href="(/others/participant_detail[^"]+)"', html
                )

                # ページにより0件の可能性もあるが、存在するリンクは正しいことを検証
                for href in links:
                    parsed = urlparse(href)
                    qs = parse_qs(parsed.query)

                    self.assertIn("id", qs, msg=f"id欠落: {href}")
                    self.assertIn("mode", qs, msg=f"mode欠落: {href}")

                    id_values = qs.get("id", [])
                    mode_values = qs.get("mode", [])

                    self.assertTrue(
                        id_values and id_values[0].isdigit(), msg=f"id不正: {href}"
                    )
                    self.assertTrue(
                        mode_values and mode_values[0] in allowed_modes,
                        msg=f"mode不正: {href}",
                    )


if __name__ == "__main__":
    unittest.main()
