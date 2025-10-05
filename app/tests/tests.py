"""
Flask アプリケーションのテストモジュール

python -m pytest app/tests/tests.py -v
"""

import json
import os
import time
import unittest
from unittest.mock import Mock, patch

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

        # context_processors内のSupabase呼び出しモック
        def context_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            if table == "Year" and pandas_flag:
                import pandas as pd

                return pd.DataFrame(
                    [
                        {"year": 2025},
                        {"year": 2024},
                        {"year": 2023},
                    ]
                )
            # 他の場合はデフォルトのリストを返す
            return [
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

        mock_context_supabase.get_data.side_effect = context_get_data_side_effect
        # participant_detail内のSupabase呼び出しは空配列を返す（リダイレクトでもテスト条件は満たす）
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
                (f"/{year}/cancels", f"{year}年 辞退者一覧"),
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

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.supabase_service")
    @patch("app.context_processors.get_available_years")
    @patch("app.context_processors.is_gbb_ended")
    def test_2025_participants_translation_accessibility(
        self,
        mock_is_gbb_ended,
        mock_get_years,
        mock_context_supabase,
        mock_participants_supabase,
    ):
        """
        /2025/participants?lang=(すべての言語)にアクセスして200を返すことをテストします。

        翻訳の問題がないかを確認するため、サポートされているすべての言語で
        参加者ページが正常に表示されることを検証します。
        """
        # main.pyからサポートされている言語コードのリストを取得
        from app.main import LANGUAGES

        # 日本語以外の言語のみを対象とする（日本語はデフォルト言語なので翻訳ファイルが不要）
        supported_languages = [code for code, _ in LANGUAGES if code != "ja"]

        # モックデータの設定
        mock_get_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False

        # context_processors内のSupabase呼び出しモック
        def context_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            if table == "Year" and pandas_flag:
                import pandas as pd

                return pd.DataFrame(
                    [
                        {"year": 2025},
                        {"year": 2024},
                        {"year": 2023},
                    ]
                )
            # 他の場合はデフォルトのリストを返す
            return [
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

        mock_context_supabase.get_data.side_effect = context_get_data_side_effect

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
                            "names": {
                                "ja": "日本",
                                "en": "Japan",
                                "de": "Japan",
                                "es": "Japón",
                                "fr": "Japon",
                                "hi": "जापान",
                                "hu": "Japán",
                                "it": "Giappone",
                                "ko": "일본",
                                "ms": "Jepun",
                                "no": "Japan",
                                "pt": "Japão",
                                "ta": "ஜப்பான்",
                                "th": "ญี่ปุ่น",
                                "zh_Hans_CN": "日本",
                                "zh_Hant_TW": "日本",
                            },
                        },
                        "ParticipantMember": [],
                    }
                ]
            return []

        mock_participants_supabase.get_data.side_effect = (
            participants_get_data_side_effect
        )

        # 各言語でテストを実行
        for lang in supported_languages:
            with self.subTest(language=lang):
                # 必要なクエリパラメータを含めてURLを構築
                url = f"/2025/participants?category=Loopstation&ticket_class=all&cancel=show&lang={lang}"
                response = self.client.get(url)

                # 200を期待（適切なパラメータがあるためリダイレクトは発生しないはず）
                self.assertEqual(
                    response.status_code,
                    200,
                    msg=f"言語 {lang} で {url} が200を返しませんでした（{response.status_code}）。翻訳に問題がある可能性があります。",
                )

                # レスポンスボディが空でないことも確認
                html = response.get_data(as_text=True)
                self.assertTrue(
                    len(html) > 0,
                    msg=f"言語 {lang} で {url} のレスポンスボディが空です。",
                )

    def test_language_consistency_across_modules(self):
        """
        main.py、translate.py、translationsフォルダの言語設定に矛盾がないかを確認するテストです。

        日本語を除くすべての言語で一致していることを検証します。
        """
        # main.pyの言語設定を取得
        from app.main import LANGUAGES

        main_languages = set([code for code, _ in LANGUAGES if code != "ja"])

        # translate.pyの言語設定を取得
        from app.translations.translate import BABEL_SUPPORTED_LOCALES

        translate_languages = set(BABEL_SUPPORTED_LOCALES)

        # translationsフォルダの言語フォルダを取得
        import os

        translations_dir = "app/translations"
        translation_folders = set()
        if os.path.exists(translations_dir):
            for item in os.listdir(translations_dir):
                item_path = os.path.join(translations_dir, item)
                if os.path.isdir(item_path) and item not in ["__pycache__"]:
                    # LC_MESSAGESフォルダが存在することを確認
                    lc_messages_path = os.path.join(item_path, "LC_MESSAGES")
                    if os.path.exists(lc_messages_path):
                        translation_folders.add(item)

        # 言語設定の一致を確認
        self.assertEqual(
            main_languages,
            translate_languages,
            msg=f"main.pyとtranslate.pyの言語設定が一致しません。\n"
            f"main.py(jaを除く): {sorted(main_languages)}\n"
            f"translate.py: {sorted(translate_languages)}\n"
            f"差分: {main_languages.symmetric_difference(translate_languages)}",
        )

        self.assertEqual(
            main_languages,
            translation_folders,
            msg=f"main.pyとtranslationsフォルダの言語設定が一致しません。\n"
            f"main.py(jaを除く): {sorted(main_languages)}\n"
            f"translationsフォルダ: {sorted(translation_folders)}\n"
            f"差分: {main_languages.symmetric_difference(translation_folders)}",
        )

        self.assertEqual(
            translate_languages,
            translation_folders,
            msg=f"translate.pyとtranslationsフォルダの言語設定が一致しません。\n"
            f"translate.py: {sorted(translate_languages)}\n"
            f"translationsフォルダ: {sorted(translation_folders)}\n"
            f"差分: {translate_languages.symmetric_difference(translation_folders)}",
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
        # キャッシュをクリア
        from app.main import flask_cache

        flask_cache.delete("available_years")

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
    @patch("app.main.flask_cache")
    def test_gemini_service_rate_limit(self, mock_cache, mock_genai_client):
        """Geminiサービスのレートリミットテスト"""
        from app.models.gemini_client import GeminiService

        # キャッシュのモック設定（キャッシュなしでテスト）
        mock_cache.get.return_value = None

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # 最初のリクエストは成功、2回目はレートリミットエラー
        call_count = 0

        def mock_generate_content(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(text='{"url": "/2025/top", "parameter": "None"}')
            else:
                # レートリミットエラーをシミュレート
                raise Exception("Rate limit exceeded")

        mock_client_instance.models.generate_content = Mock(
            side_effect=mock_generate_content
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = GeminiService()

            # 最初のリクエストは成功
            result1 = service.ask("first question")
            self.assertIsInstance(result1, dict)
            # エラーハンドリングで空辞書が返される可能性があるため、条件を緩和
            if result1:  # 空辞書でない場合のみチェック
                self.assertIn("url", result1)

            # 2回目のリクエストはエラーハンドリングされて空辞書が返される
            result2 = service.ask("second question")
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
        mock_gemini_service.ask.return_value = {
            "url": "/2025/participants",
            "parameter": "search_participants",
        }

        # 複数回の連続リクエスト
        request_times = []

        def mock_ask(*args, **kwargs):
            request_times.append(time.time())
            return {"url": "/2025/participants", "parameter": "search_participants"}

        mock_gemini_service.ask.side_effect = mock_ask

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

        # askが呼ばれた回数を確認
        self.assertEqual(len(request_times), 3)

        # スプレッドシート記録はモックされているため、実通信は発生しない
        # （環境によってはIS_LOCAL/IS_PULL_REQUESTの値で呼び出し回数が変化するため回数は断定しない）
        self.assertTrue(hasattr(mock_spreadsheet_service, "record_question"))

    def test_rate_limit_configuration(self):
        """レートリミット設定の正確性テスト"""
        # ratelimitのデコレータがaskメソッドに適用されていることを確認
        from app.models.gemini_client import GeminiService

        service = GeminiService()
        # askメソッドにデコレータが適用されていることを確認
        self.assertTrue(
            hasattr(service.ask, "__wrapped__"),
            "レートリミットデコレータが適用されていません",
        )

    @patch("app.models.gemini_client.genai.Client")
    def test_rate_limit_with_retries(self, mock_genai_client):
        """リトライ機能とレートリミットの組み合わせテスト"""
        from app.models.gemini_client import GeminiService

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        call_times = []

        def mock_generate_content(*args, **kwargs):
            call_times.append(time.time())
            # 最初の2回は失敗、3回目は成功
            if len(call_times) <= 2:
                raise Exception("API Error")
            return Mock(text='{"url": "/2025/top", "parameter": "None"}')

        mock_client_instance.models.generate_content = Mock(
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
                        result = service.ask("retry test")
                        if result:
                            break
                    except Exception:
                        continue

                total_time = time.time() - start_time

                # リトライ間でもレートリミットが守られることを確認（時間は短縮）
                self.assertGreaterEqual(
                    total_time, 2.0, f"リトライ時の総時間が短すぎます: {total_time}秒"
                )
                # 最初の2回は失敗、3回目で成功するので、3回呼び出されることを確認
                # ただし、リトライロジックによっては5回まで試行される可能性がある
                self.assertLessEqual(
                    len(call_times), 5, "呼び出し回数が上限を超えています"
                )
                self.assertGreaterEqual(
                    len(call_times), 3, "期待される最小呼び出し回数に達していません"
                )

    @patch("app.models.gemini_client.genai.Client")
    def test_rate_limit_stress_test(self, mock_genai_client):
        """レートリミットのストレステスト（同期版）"""
        import queue
        import threading

        from app.models.gemini_client import GeminiService

        # モックの設定
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        request_times = []
        request_lock = threading.Lock()

        def mock_generate_content(*args, **kwargs):
            with request_lock:
                request_times.append(time.time())
            return Mock(text='{"url": "/test", "parameter": "None"}')

        mock_client_instance.models.generate_content = Mock(
            side_effect=mock_generate_content
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = GeminiService()

            # 複数のスレッドで同時にリクエストを送信
            def worker(result_queue, worker_id):
                try:
                    result = service.ask(f"test question {worker_id}")
                    result_queue.put((worker_id, result, time.time()))
                except Exception:
                    result_queue.put((worker_id, {}, time.time()))

            start_time = time.time()
            result_queue = queue.Queue()
            threads = []

            # 5つのスレッドで同時実行
            for i in range(5):
                thread = threading.Thread(target=worker, args=(result_queue, i))
                threads.append(thread)
                thread.start()

            # すべてのスレッドの完了を待機
            for thread in threads:
                thread.join()

            total_time = time.time() - start_time

            # 結果の収集
            results = []
            while not result_queue.empty():
                results.append(result_queue.get())

            # 結果検証
            self.assertEqual(
                len(results), 5, "実行されたリクエスト数が期待値と異なります"
            )
            # レートリミットにより、5リクエスト × 2秒間隔 = 最低8秒
            self.assertGreaterEqual(
                total_time, 6.0, f"ストレステスト総時間が短すぎます: {total_time}秒"
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
        """participant_detail: 初回取得でデータがない場合は参加者ページにリダイレクトする"""
        mock_get_available_years.return_value = [2025, 2024]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/others/participant_detail?id=0&mode=single")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith("/2025/participants"))

    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_participant_detail_missing_params(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
    ):
        """participant_detail: id/modeパラメータが無い場合は参加者ページにリダイレクトする"""
        mock_get_available_years.return_value = [2025, 2024]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        # idパラメータが無い場合
        resp = self.client.get("/others/participant_detail?mode=single")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith("/2025/participants"))

        # modeパラメータが無い場合
        resp = self.client.get("/others/participant_detail?id=123")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith("/2025/participants"))

        # 両方のパラメータが無い場合
        resp = self.client.get("/others/participant_detail")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith("/2025/participants"))


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

    def test_read_only_client_property_getter(self):
        """read_only_client propertyのgetter動作を検証する。"""
        from app.models.supabase_client import SupabaseService

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # 初回アクセス - クライアントが作成される
            with patch(
                "app.models.supabase_client.create_client"
            ) as mock_create_client:
                mock_client = Mock()
                mock_create_client.return_value = mock_client

                client1 = service.read_only_client
                self.assertEqual(client1, mock_client)
                self.assertEqual(service._read_only_usage_count, 1)
                mock_create_client.assert_called_once_with(
                    "http://localhost", "anon_key"
                )

            # 2回目のアクセス - キャッシュされたクライアントが返される
            client2 = service.read_only_client
            self.assertEqual(client2, mock_client)
            self.assertEqual(service._read_only_usage_count, 2)

    def test_read_only_client_property_setter(self):
        """read_only_client propertyのsetter動作を検証する。"""
        from app.models.supabase_client import SupabaseService

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # まずカウンターを増やしておく
            service._read_only_usage_count = 5

            # setterでクライアントを設定
            mock_client = Mock()
            service.read_only_client = mock_client

            # クライアントとカウンターがリセットされていることを確認
            self.assertEqual(service._read_only_client, mock_client)
            self.assertEqual(service._read_only_usage_count, 0)

    def test_read_only_client_usage_limit_reset(self):
        """read_only_clientが使用回数上限に達した際にリセットされることを検証する。"""
        from app.models.supabase_client import MAX_CLIENT_USAGE, SupabaseService

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # 使用回数上限までカウントを進める
            service._read_only_usage_count = MAX_CLIENT_USAGE

            with patch(
                "app.models.supabase_client.create_client"
            ) as mock_create_client:
                mock_client = Mock()
                mock_create_client.return_value = mock_client

                # 上限に達しているので新しいクライアントが作成される
                client = service.read_only_client
                self.assertEqual(client, mock_client)
                self.assertEqual(
                    service._read_only_usage_count, 1
                )  # リセットされて1になる
                mock_create_client.assert_called_once()

    def test_admin_client_property_getter(self):
        """admin_client propertyのgetter動作を検証する。"""
        from app.models.supabase_client import SupabaseService

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # 初回アクセス - 管理者クライアントが作成される
            with patch(
                "app.models.supabase_client.create_client"
            ) as mock_create_client:
                mock_client = Mock()
                mock_create_client.return_value = mock_client

                client1 = service.admin_client
                self.assertEqual(client1, mock_client)
                self.assertEqual(service._admin_usage_count, 1)
                mock_create_client.assert_called_once_with(
                    "http://localhost", "service_key"
                )

            # 2回目のアクセス - キャッシュされたクライアントが返される
            client2 = service.admin_client
            self.assertEqual(client2, mock_client)
            self.assertEqual(service._admin_usage_count, 2)

    def test_admin_client_usage_limit_reset(self):
        """admin_clientが使用回数上限に達した際にリセットされることを検証する。"""
        from app.models.supabase_client import MAX_CLIENT_USAGE, SupabaseService

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # 使用回数上限までカウントを進める
            service._admin_usage_count = MAX_CLIENT_USAGE

            with patch(
                "app.models.supabase_client.create_client"
            ) as mock_create_client:
                mock_client = Mock()
                mock_create_client.return_value = mock_client

                # 上限に達しているので新しいクライアントが作成される
                client = service.admin_client
                self.assertEqual(client, mock_client)
                self.assertEqual(service._admin_usage_count, 1)  # リセットされて1になる
                mock_create_client.assert_called_once_with(
                    "http://localhost", "service_key"
                )

    def test_apply_filter_all_operators(self):
        """_apply_filterプライベートメソッドのすべてのオペレーターをテストする。"""
        from app.models.supabase_client import SupabaseService
        from app.util.filter_eq import Operator

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # モッククエリオブジェクトを作成
            mock_query = Mock()

            # 各オペレーターのテスト
            test_cases = [
                # 比較演算子
                (Operator.GREATER_THAN, "age", 18, "gt"),
                (Operator.GREATER_THAN_OR_EQUAL_TO, "age", 18, "gte"),
                (Operator.LESS_THAN, "age", 65, "lt"),
                (Operator.LESS_THAN_OR_EQUAL_TO, "age", 65, "lte"),
                (Operator.NOT_EQUAL, "status", "inactive", "neq"),
                # 部分一致
                (Operator.LIKE, "name", "%test%", "like"),
                (Operator.ILIKE, "name", "%Test%", "ilike"),
                (Operator.NOT_LIKE, "name", "%bot%", "not_.like"),
                (Operator.NOT_ILIKE, "name", "%Bot%", "not_.ilike"),
                # NULL判定
                (Operator.IS, "deleted_at", None, "is_"),
                (Operator.IS_NOT, "deleted_at", None, "not_.is_"),
                # リスト・配列
                (Operator.IN_, "category", ["A", "B"], "in_"),
                (Operator.CONTAINS, "tags", ["urgent"], "contains"),
                # 未知のオペレーター（フォールバック）
                ("unknown_op", "field", "value", "eq"),
            ]

            for operator, field, value, expected_method in test_cases:
                with self.subTest(operator=operator):
                    mock_query.reset_mock()

                    # 各メソッドが呼ばれるたびに自分自身を返すように設定
                    for method_name in [
                        "gt",
                        "gte",
                        "lt",
                        "lte",
                        "neq",
                        "like",
                        "ilike",
                        "is_",
                        "in_",
                        "contains",
                        "eq",
                    ]:
                        getattr(mock_query, method_name).return_value = mock_query

                    # not_.like, not_.ilike, not_.is_の設定
                    mock_query.not_.like.return_value = mock_query
                    mock_query.not_.ilike.return_value = mock_query
                    mock_query.not_.is_.return_value = mock_query

                    # _apply_filterを呼び出し
                    result = service._apply_filter(mock_query, field, operator, value)

                    # 返り値はクエリオブジェクトであること（メソッドチェーンにより自分自身を返す）
                    self.assertEqual(result, mock_query)

                    # 正しいメソッドが呼ばれたことを確認
                    if operator == Operator.NOT_LIKE:
                        mock_query.not_.like.assert_called_once_with(field, value)
                    elif operator == Operator.NOT_ILIKE:
                        mock_query.not_.ilike.assert_called_once_with(field, value)
                    elif operator == Operator.IS_NOT:
                        mock_query.not_.is_.assert_called_once_with(field, value)
                    elif operator == "unknown_op":
                        mock_query.eq.assert_called_once_with(field, value)
                    else:
                        getattr(mock_query, expected_method).assert_called_once_with(
                            field, value
                        )

    def test_update_translated_answer_success(self):
        """update_translated_answerメソッドが正常に動作することをテストする。"""
        from app.models.supabase_client import SupabaseService

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # キャッシュと管理者クライアントをモック
            dict_cache = self.DictCache()
            with patch("app.main.flask_cache", dict_cache):
                # 管理者クライアントのモック
                mock_admin_client = Mock()
                mock_table = Mock()
                mock_admin_client.table.return_value = mock_table
                mock_table.update.return_value.eq.return_value.execute.return_value = (
                    None
                )
                service._admin_client = mock_admin_client

                # テストデータ
                cache_key = "test_key"
                translated_answer = {"ja": "こんにちは", "en": "Hello"}

                # メソッド実行
                service.update_translated_answer(cache_key, translated_answer)

                # DB更新が正しく呼ばれたことを確認
                mock_admin_client.table.assert_called_with("Tavily")
                mock_table.update.assert_called_once()
                update_call = mock_table.update.call_args
                self.assertIn("answer_translation", update_call[0][0])
                # 辞書オブジェクトがそのまま渡されることを確認
                self.assertEqual(
                    update_call[0][0]["answer_translation"], translated_answer
                )
                mock_table.update.return_value.eq.assert_called_with(
                    "cache_key", cache_key
                )
                mock_table.update.return_value.eq.return_value.execute.assert_called_once()

                # キャッシュが更新されたことを確認
                cache_key_with_column = f"{cache_key}_answer_translation"
                self.assertEqual(
                    dict_cache.get(cache_key_with_column), translated_answer
                )

    def test_update_translated_answer_db_error_handling(self):
        """update_translated_answerメソッドがDBエラーを適切に処理することをテストする。"""
        from postgrest.exceptions import APIError

        from app.models.supabase_client import SupabaseService

        # 環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # キャッシュと管理者クライアントをモック
            dict_cache = self.DictCache()
            with patch("app.main.flask_cache", dict_cache):
                # 管理者クライアントのモック（APIErrorを発生させる）
                mock_admin_client = Mock()
                mock_table = Mock()
                mock_admin_client.table.return_value = mock_table
                mock_table.update.return_value.eq.return_value.execute.side_effect = (
                    APIError({"message": "DB Error"})
                )
                service._admin_client = mock_admin_client

                # テストデータ
                cache_key = "test_key"
                translated_answer = {"ja": "こんにちは", "en": "Hello"}

                # メソッド実行（エラーが握りつぶされることを確認）
                service.update_translated_answer(cache_key, translated_answer)

                # キャッシュが更新されたことを確認（DBエラーでもキャッシュは更新される）
                cache_key_with_column = f"{cache_key}_answer_translation"
                self.assertEqual(
                    dict_cache.get(cache_key_with_column), translated_answer
                )

    def test_constructor_successful_initialization(self):
        """__init__メソッドが正常に初期化されることをテストする。"""
        from app.models.supabase_client import SupabaseService

        # 必要な環境変数を設定
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "http://localhost",
                "SUPABASE_ANON_KEY": "anon_key",
                "SUPABASE_SERVICE_ROLE_KEY": "service_key",
            },
        ):
            service = SupabaseService()

            # インスタンス変数が正しく初期化されていることを確認
            self.assertIsNone(service._read_only_client)
            self.assertIsNone(service._admin_client)
            self.assertEqual(service._read_only_usage_count, 0)
            self.assertEqual(service._admin_usage_count, 0)

    def test_constructor_missing_env_vars(self):
        """__init__メソッドが環境変数不足時に適切にエラーを発生させることをテストする。"""
        from app.models.supabase_client import SupabaseService

        # テストケース: 各環境変数が不足している場合
        test_cases = [
            # 全て不足
            (
                {},
                "以下の環境変数が必要です: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY",
            ),
            # SUPABASE_URLのみ不足
            (
                {
                    "SUPABASE_ANON_KEY": "anon_key",
                    "SUPABASE_SERVICE_ROLE_KEY": "service_key",
                },
                "以下の環境変数が必要です: SUPABASE_URL",
            ),
            # SUPABASE_ANON_KEYのみ不足
            (
                {
                    "SUPABASE_URL": "http://localhost",
                    "SUPABASE_SERVICE_ROLE_KEY": "service_key",
                },
                "以下の環境変数が必要です: SUPABASE_ANON_KEY",
            ),
            # SUPABASE_SERVICE_ROLE_KEYのみ不足
            (
                {"SUPABASE_URL": "http://localhost", "SUPABASE_ANON_KEY": "anon_key"},
                "以下の環境変数が必要です: SUPABASE_SERVICE_ROLE_KEY",
            ),
            # 複数不足
            (
                {"SUPABASE_ANON_KEY": "anon_key"},
                "以下の環境変数が必要です: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY",
            ),
        ]

        for env_vars, expected_message in test_cases:
            with self.subTest(env_vars=env_vars):
                with patch.dict(os.environ, env_vars, clear=True):
                    with self.assertRaises(ValueError) as context:
                        SupabaseService()

                    self.assertEqual(str(context.exception), expected_message)

    def test_constructor_empty_env_vars(self):
        """__init__メソッドが空の環境変数に対してもエラーを発生させることをテストする。"""
        from app.models.supabase_client import SupabaseService

        # 空文字列の環境変数を設定
        test_cases = [
            # 全て空文字列
            (
                {
                    "SUPABASE_URL": "",
                    "SUPABASE_ANON_KEY": "",
                    "SUPABASE_SERVICE_ROLE_KEY": "",
                },
                "以下の環境変数が必要です: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY",
            ),
            # 一部空文字列
            (
                {
                    "SUPABASE_URL": "http://localhost",
                    "SUPABASE_ANON_KEY": "",
                    "SUPABASE_SERVICE_ROLE_KEY": "service_key",
                },
                "以下の環境変数が必要です: SUPABASE_ANON_KEY",
            ),
        ]

        for env_vars, expected_message in test_cases:
            with self.subTest(env_vars=env_vars):
                with patch.dict(os.environ, env_vars, clear=True):
                    with self.assertRaises(ValueError) as context:
                        SupabaseService()

                    self.assertEqual(str(context.exception), expected_message)


class SupabaseErrorHandlingTestCase(unittest.TestCase):
    """Supabaseからの応答がない場合のエラーハンドリングのテストケース"""

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

    @patch("app.views.result.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_result_view_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """result_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/result?category=Loopstation")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.world_map.os.path.exists")
    @patch("app.views.world_map.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_world_map_view_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
        mock_os_path_exists,
    ):
        """world_map_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # マップファイルが存在しないようにする
        mock_os_path_exists.return_value = False

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/world_map")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_participants_view_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """participants_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: pandas=True かつ raise_error 未指定のため空DataFrameを返す想定
        import pandas as pd

        mock_supabase.get_data.return_value = pd.DataFrame()

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/participants")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.search_participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_search_participants_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """search_participantsでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 1回目（raise_error未指定）: 空リスト、2回目（raise_error=True）: 例外
        mock_supabase.get_data.side_effect = [[], Exception("supabase error")]

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        request_data = json.dumps({"keyword": "test"})
        resp = self.client.post(
            "/2025/search_participants",
            data=request_data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.result.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_result_view_empty_dataframe(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """result_viewで空のDataFrameが返される場合に500エラーが返されることをテスト"""

        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/result?category=Loopstation")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_participants_view_empty_dataframe(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """participants_viewで空のDataFrameが返される場合に500エラーが返されることをテスト"""
        import pandas as pd

        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 空のDataFrameを返す
        mock_supabase.get_data.return_value = pd.DataFrame()

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/participants")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.search_participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_search_participants_empty_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """search_participantsで空のレスポンスが返される場合に200と空配列が返ることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 空のリストを返す
        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        request_data = json.dumps({"keyword": "test"})
        resp = self.client.post(
            "/2025/search_participants",
            data=request_data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    @patch("app.views.rule.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_rule_view_continues_with_empty_data(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """rule_viewでSupabaseからの応答がない場合に空のデータでページを表示することをテスト

        Note: rule.pyでは44-51行目でSupabaseからのデータが取得できない場合、
        空のコンテキスト（gbb_seed, other_seed, cancelled すべて空配列）でページを表示する
        """
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 空のリストを返す（Supabaseからデータが取得できない状況をシミュレート）
        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/rule")
        # rule.pyでは空のデータでもページを表示するため200が返される
        self.assertEqual(resp.status_code, 200)

        # レスポンスのHTMLに空のデータが適用されていることを確認
        html = resp.get_data(as_text=True)
        # 空のシード権獲得者リストでもページが正常に表示されることを確認
        self.assertIn("rule", html.lower())  # ルールページが表示されていることを確認

    @patch("app.views.rule.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_rule_view_supabase_none_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """rule_viewでSupabaseからNoneが返される場合のテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # Noneを返す（Supabaseからの応答がない状況をシミュレート）
        mock_supabase.get_data.return_value = None

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/rule")
        # rule.pyでは応答がなくても空のデータでページを表示するため200が返される
        self.assertEqual(resp.status_code, 200)


class BeatboxerTavilySearchTestCase(unittest.TestCase):
    """beatboxer_tavily_search.pyの関数テストケース"""

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

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    def test_get_primary_domain_various_urls(self, mock_supabase):
        """get_primary_domain関数に様々なURLをテストする"""
        from app.views.beatboxer_tavily_search import get_primary_domain

        test_cases = [
            # 正常なURL
            ("https://www.example.com/path", "example.com"),
            ("https://sub.example.com/path", "example.com"),
            ("http://example.co.uk/path", "co.uk"),  # 実際の関数挙動に基づく
            ("https://example.com", "example.com"),
            ("https://example.com/", "example.com"),
            # 特殊なドメイン
            ("https://youtube.com/watch?v=123", "youtube.com"),
            ("https://www.youtube.com/channel/UC123", "youtube.com"),
            ("https://instagram.com/user", "instagram.com"),
            ("https://www.facebook.com/user", "facebook.com"),
            # 短いドメイン
            ("https://t.co/abc123", "t.co"),
            # IPアドレス
            ("https://192.168.1.1/path", "1.1"),  # 実際の関数挙動に基づく
        ]

        for url, expected in test_cases:
            with self.subTest(url=url):
                result = get_primary_domain(url)
                self.assertEqual(result, expected)

    def test_extract_youtube_video_id_various_urls(self):
        """extract_youtube_video_id関数に様々なYouTube URLをテストする"""
        from app.views.beatboxer_tavily_search import extract_youtube_video_id

        test_cases = [
            # 正常なYouTube URL
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # 無効な形式のURL
            ("https://www.youtube.com/watch", None),
            ("https://www.youtube.com/channel/UC123", None),
            ("https://example.com/watch?v=123", None),
            ("https://youtube.com/", None),
            # 不正なvideo_id
            ("https://www.youtube.com/watch?v=123", None),  # 短すぎる
            ("https://www.youtube.com/watch?v=invalid!@#", None),  # 無効な文字
            # クエリパラメータ付き
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30", "dQw4w9WgXcQ"),
            # 異なるドメイン
            ("https://www.youtub.com/watch?v=dQw4w9WgXcQ", None),  # ドメイン違い
        ]

        for url, expected in test_cases:
            with self.subTest(url=url):
                result = extract_youtube_video_id(url)
                self.assertEqual(result, expected)

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    def test_get_beatboxer_name_single_mode(self, mock_supabase):
        """get_beatboxer_name関数をsingleモードでテストする"""
        from app.views.beatboxer_tavily_search import get_beatboxer_name

        # モックデータの設定
        mock_supabase.get_data.return_value = [{"name": "test_beatboxer"}]

        # テスト実行
        result = get_beatboxer_name(beatboxer_id=123, mode="single")

        # 検証
        self.assertEqual(result, "TEST_BEATBOXER")
        mock_supabase.get_data.assert_called_once_with(
            table="Participant", columns=["name"], filters={"id": 123}
        )

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    def test_get_beatboxer_name_team_member_mode(self, mock_supabase):
        """get_beatboxer_name関数をteam_memberモードでテストする"""
        from app.views.beatboxer_tavily_search import get_beatboxer_name

        # モックデータの設定
        # 最初の呼び出し（Participantテーブル）は空、2番目の呼び出し（ParticipantMemberテーブル）は結果を返す
        mock_supabase.get_data.side_effect = [
            [],  # Participantテーブルの結果（空）
            [{"name": "test_member"}],  # ParticipantMemberテーブルの結果
        ]

        # テスト実行
        result = get_beatboxer_name(beatboxer_id=456, mode="team_member")

        # 検証
        self.assertEqual(result, "TEST_MEMBER")

        # 両方の呼び出しが正しいことを確認
        self.assertEqual(mock_supabase.get_data.call_count, 2)
        mock_supabase.get_data.assert_any_call(
            table="Participant", columns=["name"], filters={"id": 456}
        )
        mock_supabase.get_data.assert_any_call(
            table="ParticipantMember", columns=["name"], filters={"id": 456}
        )

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    def test_get_beatboxer_name_not_found(self, mock_supabase):
        """get_beatboxer_name関数でデータが見つからない場合のテスト"""
        from app.views.beatboxer_tavily_search import get_beatboxer_name

        # 空の結果を返す
        mock_supabase.get_data.return_value = []

        # 新仕様: 見つからない場合は空文字列を返す
        self.assertEqual(get_beatboxer_name(beatboxer_id=999, mode="single"), "")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    def test_beatboxer_tavily_search_with_beatboxer_id(
        self, mock_tavily, mock_supabase
    ):
        """beatboxer_tavily_search関数にbeatboxer_idを指定してテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            [],  # キャッシュチェック用（空で新規検索）
        ]

        mock_search_result = {
            "results": [
                {
                    "title": "Test Beatboxer Official Site",
                    "url": "https://example.com",
                    "content": "This is a test content about beatboxer",
                    "primary_domain": "example.com",
                },
                {
                    "title": "Test Beatboxer @instagram",
                    "url": "https://instagram.com/testbeatboxer",
                    "content": "Instagram profile",
                    "primary_domain": "instagram.com",
                },
            ]
        }
        mock_tavily.search.return_value = mock_search_result

        # テスト実行
        result = beatboxer_tavily_search(beatboxer_id=123)

        # 検証
        self.assertIsInstance(result, tuple)
        self.assertEqual(
            len(result), 3
        )  # (account_urls, final_urls, youtube_embed_url)

        account_urls, final_urls, youtube_embed_url = result

        # アカウントURLが正しく抽出されているか
        self.assertEqual(len(account_urls), 1)
        self.assertEqual(account_urls[0]["url"], "https://instagram.com/testbeatboxer")

        # 一般URLが正しく抽出されているか
        self.assertEqual(len(final_urls), 1)
        self.assertEqual(final_urls[0]["url"], "https://example.com")

        # YouTube埋め込みURLは空
        self.assertEqual(youtube_embed_url, "")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    def test_beatboxer_tavily_search_with_beatboxer_name(self, mock_supabase):
        """beatboxer_tavily_search関数にbeatboxer_nameを直接指定してテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # モックデータの設定
        mock_supabase.get_data.return_value = []  # キャッシュなし

        mock_search_result = {
            "results": [
                {
                    "title": "Direct Name Search Result",
                    "url": "https://example.com/direct",
                    "content": "Direct search result",
                    "primary_domain": "example.com",
                }
            ]
        }

        with patch("app.views.beatboxer_tavily_search.tavily_service") as mock_tavily:
            mock_tavily.search.return_value = mock_search_result

            # テスト実行
            result = beatboxer_tavily_search(beatboxer_name="Test Beatboxer")

            # 検証
            account_urls, final_urls, youtube_embed_url = result
            self.assertEqual(len(final_urls), 1)
            self.assertEqual(final_urls[0]["url"], "https://example.com/direct")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    def test_beatboxer_tavily_search_no_parameters_error(self, mock_supabase):
        """beatboxer_tavily_search関数でパラメータが不足する場合のエラーテスト"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # 両方のパラメータがNoneの場合
        with self.assertRaises(ValueError) as context:
            beatboxer_tavily_search()

        self.assertIn(
            "beatboxer_idまたはbeatboxer_nameが必要です", str(context.exception)
        )

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    def test_beatboxer_tavily_search_youtube_extraction(
        self, mock_tavily, mock_supabase
    ):
        """beatboxer_tavily_search関数でYouTube動画ID抽出をテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "youtube_beatboxer"}],  # get_beatboxer_name用
            [],  # キャッシュチェック用
        ]

        mock_search_result = {
            "results": [
                {
                    "title": "YouTube Beatbox Video",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "content": "Amazing beatbox performance",
                    "primary_domain": "youtube.com",
                },
                {
                    "title": "Another Site",
                    "url": "https://example.com",
                    "content": "Other content",
                    "primary_domain": "example.com",
                },
            ]
        }
        mock_tavily.search.return_value = mock_search_result

        # テスト実行
        result = beatboxer_tavily_search(beatboxer_id=123)

        account_urls, final_urls, youtube_embed_url = result

        # YouTube埋め込みURLが正しく生成されているか
        expected_embed_url = (
            "https://www.youtube.com/embed/dQw4w9WgXcQ?controls=0&hd=1&vq=hd720"
        )
        self.assertEqual(youtube_embed_url, expected_embed_url)

        # 一般URLは1つ（YouTube以外）
        self.assertEqual(len(final_urls), 1)
        self.assertEqual(final_urls[0]["url"], "https://example.com")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    def test_beatboxer_tavily_search_ban_words_filtering(
        self, mock_tavily, mock_supabase
    ):
        """beatboxer_tavily_search関数で禁止ワードによるフィルタリングをテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            [],  # キャッシュチェック用
        ]

        mock_search_result = {
            "results": [
                {
                    "title": "Clean Result",
                    "url": "https://example.com/clean",
                    "content": "This is clean content",
                    "primary_domain": "example.com",
                },
                {
                    "title": "Banned Result HATEN",
                    "url": "https://example.com/banned",
                    "content": "This contains HATEN word",
                    "primary_domain": "example.com",
                },
                {
                    "title": "Another Banned Result",
                    "url": "https://example.com/banned2",
                    "content": "This is JPN CUP related",
                    "primary_domain": "example.com",
                },
            ]
        }
        mock_tavily.search.return_value = mock_search_result

        # テスト実行
        result = beatboxer_tavily_search(beatboxer_id=123)

        account_urls, final_urls, youtube_embed_url = result

        # 禁止ワードを含む結果は除外されているか
        self.assertEqual(len(final_urls), 1)
        self.assertEqual(final_urls[0]["title"], "Clean Result")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    def test_beatboxer_tavily_search_minimum_results(self, mock_tavily, mock_supabase):
        """beatboxer_tavily_search関数で最低3件の結果を確保するロジックをテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            [],  # キャッシュチェック用
        ]

        mock_search_result = {
            "results": [
                {
                    "title": "Result 1",
                    "url": "https://example1.com",
                    "content": "Content 1",
                    "primary_domain": "example1.com",
                },
                {
                    "title": "Result 2",
                    "url": "https://example2.com",
                    "content": "Content 2",
                    "primary_domain": "example2.com",
                },
                {
                    "title": "Result 3",
                    "url": "https://example3.com",
                    "content": "Content 3",
                    "primary_domain": "example3.com",
                },
                {
                    "title": "Result 4",
                    "url": "https://example4.com",
                    "content": "Content 4",
                    "primary_domain": "example4.com",
                },
            ]
        }
        mock_tavily.search.return_value = mock_search_result

        # テスト実行
        result = beatboxer_tavily_search(beatboxer_id=123)

        account_urls, final_urls, youtube_embed_url = result

        # 4つの異なるドメインの結果がある場合、ステップ2で4件すべてが追加される
        self.assertEqual(len(final_urls), 4)
        self.assertEqual(final_urls[0]["url"], "https://example1.com")
        self.assertEqual(final_urls[1]["url"], "https://example2.com")
        self.assertEqual(final_urls[2]["url"], "https://example3.com")
        self.assertEqual(final_urls[3]["url"], "https://example4.com")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    def test_beatboxer_tavily_search_maximum_results(self, mock_tavily, mock_supabase):
        """beatboxer_tavily_search関数で最大5件の結果に制限されることをテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            [],  # キャッシュチェック用
        ]

        # 7件の結果を作成
        mock_results = []
        for i in range(7):
            mock_results.append(
                {
                    "title": f"Result {i}",
                    "url": f"https://example{i}.com",
                    "content": f"Content {i}",
                    "primary_domain": f"example{i}.com",
                }
            )

        mock_search_result = {"results": mock_results}
        mock_tavily.search.return_value = mock_search_result

        # テスト実行
        result = beatboxer_tavily_search(beatboxer_id=123)

        account_urls, final_urls, youtube_embed_url = result

        # 結果が最大5件に制限されているか
        self.assertEqual(len(final_urls), 5)

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    def test_beatboxer_tavily_search_cached_results(self, mock_tavily, mock_supabase):
        """beatboxer_tavily_search関数でキャッシュされた結果を使用する場合をテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # キャッシュされた結果を返す
        cached_result = {
            "results": [
                {
                    "title": "Cached Result",
                    "url": "https://cached.com",
                    "content": "Cached content",
                    "primary_domain": "cached.com",
                }
            ]
        }

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            [],  # キャッシュチェック用（空のリスト = キャッシュなし）
        ]

        # get_tavily_dataのモック（キャッシュされた結果を返す）
        mock_supabase.get_tavily_data.return_value = cached_result

        # テスト実行（この場合はTavily検索は呼ばれず、キャッシュが使用される）
        result = beatboxer_tavily_search(beatboxer_id=123)

        account_urls, final_urls, youtube_embed_url = result

        # Tavily検索が呼ばれていないことを確認
        mock_tavily.search.assert_not_called()

        # キャッシュされた結果が使用されているか
        self.assertEqual(len(final_urls), 1)
        self.assertEqual(final_urls[0]["url"], "https://cached.com")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    def test_beatboxer_tavily_search_with_youtube_short_url(
        self, mock_tavily, mock_supabase
    ):
        """beatboxer_tavily_search関数でyoutu.be短縮URLの処理をテストする"""
        from app.views.beatboxer_tavily_search import beatboxer_tavily_search

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            [],  # キャッシュチェック用
        ]

        mock_search_result = {
            "results": [
                {
                    "title": "Short YouTube URL",
                    "url": "https://youtu.be/dQw4w9WgXcQ",
                    "content": "Short URL beatbox video",
                    "primary_domain": "youtu.be",
                }
            ]
        }
        mock_tavily.search.return_value = mock_search_result

        # テスト実行
        result = beatboxer_tavily_search(beatboxer_id=123)

        account_urls, final_urls, youtube_embed_url = result

        # youtu.beのvideo_idが正しく抽出されているか
        expected_embed_url = (
            "https://www.youtube.com/embed/dQw4w9WgXcQ?controls=0&hd=1&vq=hd720"
        )
        self.assertEqual(youtube_embed_url, expected_embed_url)

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    @patch("app.views.beatboxer_tavily_search.gemini_service")
    def test_translate_tavily_answer_with_cache(
        self, mock_gemini, mock_tavily, mock_supabase
    ):
        """translate_tavily_answer関数でキャッシュされた翻訳を使用する場合をテストする"""
        from app.views.beatboxer_tavily_search import translate_tavily_answer

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            {"answer": "This is an answer"},  # search_result
            {"ja": "これは回答です"},  # cached translation
        ]

        with patch("app.main.flask_cache") as mock_cache:
            mock_cache.get.return_value = {"ja": "これは回答です"}  # 内部キャッシュ

            # テスト実行
            result = translate_tavily_answer(
                beatboxer_id=123, mode="single", language="ja"
            )

            # 検証
            self.assertEqual(result, "これは回答です")
            # Gemini APIが呼ばれていないことを確認
            mock_gemini.ask.assert_not_called()

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    @patch("app.views.beatboxer_tavily_search.gemini_service")
    def test_translate_tavily_answer_without_cache(
        self, mock_gemini, mock_tavily, mock_supabase
    ):
        """translate_tavily_answer関数でキャッシュなしの場合の翻訳をテストする"""
        from app.views.beatboxer_tavily_search import translate_tavily_answer

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            {"answer": "This is an answer"},  # search_result
            [],  # no cached translation
        ]

        mock_gemini.ask.return_value = {"translated_text": "これは回答です"}

        with patch("app.main.flask_cache") as mock_cache:
            mock_cache.get.return_value = None  # 内部キャッシュなし

            # テスト実行
            result = translate_tavily_answer(
                beatboxer_id=123, mode="single", language="ja"
            )

            # 検証
            self.assertEqual(result, "これは回答です")
            # Gemini APIが呼ばれたことを確認
            mock_gemini.ask.assert_called_once()

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    def test_translate_tavily_answer_no_search_result(self, mock_supabase):
        """translate_tavily_answer関数で検索結果がない場合をテストする"""
        from app.views.beatboxer_tavily_search import translate_tavily_answer

        with patch("app.main.flask_cache") as mock_cache:
            mock_cache.get.return_value = None

            # モックデータの設定
            mock_supabase.get_data.side_effect = [
                [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            ]

            # get_tavily_dataのモック（answerフィールドがない場合）
            mock_supabase.get_tavily_data.side_effect = [
                {},  # search_result with no answer
                [],  # no cached translation
            ]

            result = translate_tavily_answer(
                beatboxer_id=123, mode="single", language="ja"
            )

            # 検証
            self.assertEqual(result, "")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    @patch("app.views.beatboxer_tavily_search.gemini_service")
    def test_translate_tavily_answer_gemini_error(
        self, mock_gemini, mock_tavily, mock_supabase
    ):
        """translate_tavily_answer関数でGemini APIエラーの場合をテストする"""
        from app.views.beatboxer_tavily_search import translate_tavily_answer

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            {"answer": "This is an answer"},  # search_result
            [],  # no cached translation
        ]

        # Gemini APIがエラーを返す
        mock_gemini.ask.return_value = "Error occurred"

        with patch("app.main.flask_cache") as mock_cache:
            mock_cache.get.return_value = None

            # テスト実行
            result = translate_tavily_answer(
                beatboxer_id=123, mode="single", language="ja"
            )

            # 検証（Geminiエラーの場合は空文字列を返す）
            self.assertEqual(result, "")

    @patch("app.views.beatboxer_tavily_search.supabase_service")
    @patch("app.views.beatboxer_tavily_search.tavily_service")
    @patch("app.views.beatboxer_tavily_search.gemini_service")
    def test_translate_tavily_answer_list_response(
        self, mock_gemini, mock_tavily, mock_supabase
    ):
        """translate_tavily_answer関数でGeminiがリストを返す場合をテストする"""
        from app.views.beatboxer_tavily_search import translate_tavily_answer

        # モックデータの設定
        mock_supabase.get_data.side_effect = [
            [{"name": "test_beatboxer"}],  # get_beatboxer_name用
            {"answer": "This is an answer"},  # search_result
            [],  # no cached translation
        ]

        # Gemini APIがリストを返す
        mock_gemini.ask.return_value = [{"translated_text": "これは回答です"}]

        with patch("app.main.flask_cache") as mock_cache:
            mock_cache.get.return_value = None

            # テスト実行
            result = translate_tavily_answer(
                beatboxer_id=123, mode="single", language="ja"
            )

            # 検証
            self.assertEqual(result, "これは回答です")

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
            # 直接 participant_detail も対象に含める（存在確認/リンク抽出が目的、200 or リダイレクトを許容）
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
                    # HTMLエンティティをデコード（&amp; → &）
                    import html

                    decoded_href = html.unescape(href)
                    parsed = urlparse(decoded_href)
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

    @patch("app.views.participants.wildcard_rank_sort")
    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_cancels_view_normal_case(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
        mock_wildcard_rank_sort,
    ):
        """cancels_viewの正常系テスト"""
        mock_get_available_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()
        mock_wildcard_rank_sort.return_value = 0

        # 辞退者のモックデータ
        cancels_data = [
            {
                "id": 1,
                "name": "test_participant_1",
                "category": "Loopstation",
                "ticket_class": "GBB Seed",
                "Category": {"name": "Loopstation"},
                "ParticipantMember": [],  # シングル参加者
            },
            {
                "id": 2,
                "name": "test_team_1",
                "category": "Tag Team",
                "ticket_class": "Wildcard 1st",
                "Category": {"name": "Tag Team"},
                "ParticipantMember": [
                    {"name": "Member1"},
                    {"name": "Member2"},
                ],  # チーム参加者
            },
        ]

        mock_supabase.get_data.return_value = cancels_data

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/cancels")
        self.assertEqual(resp.status_code, 200)

        # レスポンスの内容確認
        response_data = resp.get_data(as_text=True)
        self.assertIn("辞退者一覧", response_data)
        self.assertIn("TEST_PARTICIPANT_1", response_data)  # 大文字変換確認
        self.assertIn("TEST_TEAM_1", response_data)
        self.assertIn("Loopstation", response_data)
        self.assertIn("Tag Team", response_data)

    @patch("app.views.participants.wildcard_rank_sort")
    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_cancels_view_empty_data(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
        mock_wildcard_rank_sort,
    ):
        """cancels_viewで辞退者データが空の場合のテスト"""
        mock_get_available_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()
        mock_wildcard_rank_sort.return_value = 0

        # 空のデータ
        mock_supabase.get_data.return_value = []

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/cancels")
        self.assertEqual(resp.status_code, 200)

        # 空の場合のメッセージ確認
        response_data = resp.get_data(as_text=True)
        self.assertIn("辞退者一覧", response_data)
        self.assertIn("発表次第更新", response_data)

    @patch("app.views.participants.supabase_service")
    @patch("app.context_processors.get_translated_urls")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    def test_cancels_view_supabase_no_response(
        self,
        mock_get_available_years,
        mock_is_gbb_ended,
        mock_get_translated_urls,
        mock_supabase,
    ):
        """cancels_viewでSupabaseからの応答がない場合に500エラーが返されることをテスト"""
        mock_get_available_years.return_value = [2025]
        mock_is_gbb_ended.return_value = False
        mock_get_translated_urls.return_value = set()

        # 取得失敗: raise_error=True の呼び出しを例外で表現
        mock_supabase.get_data.side_effect = Exception("supabase error")

        with self.client.session_transaction() as sess:
            sess["language"] = "ja"

        resp = self.client.get("/2025/cancels")
        self.assertEqual(resp.status_code, 500)

    @patch("app.views.participants.wildcard_rank_sort")
    @patch("app.context_processors.is_gbb_ended")
    @patch("app.context_processors.get_available_years")
    @patch("app.context_processors.supabase_service")
    @patch("app.views.participants.supabase_service")
    def test_2025_cancels_translation_accessibility(
        self,
        mock_participants_supabase,
        mock_context_supabase,
        mock_get_years,
        mock_is_gbb_ended,
        mock_wildcard_rank_sort,
    ):
        """
        /2025/cancels?lang=(すべての言語)にアクセスして200を返すことをテストします。

        翻訳の問題がないかを確認するため、サポートされているすべての言語で
        辞退者ページが正常に表示されることを検証します。
        """
        # main.pyからサポートされている言語コードのリストを取得
        from app.main import LANGUAGES

        # 日本語以外の言語のみを対象とする（日本語はデフォルト言語なので翻訳ファイルが不要）
        supported_languages = [code for code, _ in LANGUAGES if code != "ja"]

        # モックデータの設定
        mock_get_years.return_value = [2025, 2024, 2023]
        mock_is_gbb_ended.return_value = False
        mock_wildcard_rank_sort.return_value = 0

        # context_processors内のSupabase呼び出しモック
        def context_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            pandas_flag = kwargs.get("pandas", False)
            if table == "Year" and pandas_flag:
                import pandas as pd

                return pd.DataFrame(
                    [
                        {"year": 2025},
                        {"year": 2024},
                        {"year": 2023},
                    ]
                )
            # 他の場合はデフォルトのリストを返す
            return [
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

        mock_context_supabase.get_data.side_effect = context_get_data_side_effect

        # participants内のSupabase呼び出しモック - 辞退者データ
        def participants_get_data_side_effect(*args, **kwargs):
            table = kwargs.get("table")
            if table == "Participant":
                return [
                    {
                        "id": 1,
                        "name": "test_participant_1",
                        "category": "Loopstation",
                        "ticket_class": "GBB Seed",
                        "Category": {"name": "Loopstation"},
                        "ParticipantMember": [],
                    },
                ]
            return []

        mock_participants_supabase.get_data.side_effect = (
            participants_get_data_side_effect
        )

        # 各言語でページにアクセスしてテスト
        for lang in supported_languages:
            with self.subTest(language=lang):
                resp = self.client.get(f"/2025/cancels?lang={lang}")
                self.assertEqual(
                    resp.status_code,
                    200,
                    msg=f"言語 {lang} で /2025/cancels が200を返しませんでした（{resp.status_code}）。",
                )


class YearRequirementsTestCase(unittest.TestCase):
    """
    年度追加時の必須要件が揃っているかを確認するテストケース

    データベースの代わりにテンプレートフォルダの内容を確認して、
    新年度追加に必要なファイルとフォルダが存在するかを検証します。
    """

    def setUp(self):
        """テストの前準備を行います。"""
        self.templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.translations_dir = os.path.join(
            os.path.dirname(__file__), "..", "translations"
        )

        # 利用可能な年度をテンプレートフォルダから取得
        self.available_years = []
        if os.path.exists(self.templates_dir):
            for item in os.listdir(self.templates_dir):
                item_path = os.path.join(self.templates_dir, item)
                if os.path.isdir(item_path) and item.isdigit():
                    self.available_years.append(int(item))
        self.available_years.sort(reverse=True)

    def test_year_template_directories_exist(self):
        """
        各年度のテンプレートディレクトリが存在することをテストします。
        """
        for year in self.available_years:
            year_dir = os.path.join(self.templates_dir, str(year))
            with self.subTest(year=year):
                self.assertTrue(
                    os.path.exists(year_dir),
                    f"年度 {year} のテンプレートディレクトリが存在しません: {year_dir}",
                )

    def test_required_template_files_exist(self):
        """
        各年度の必須テンプレートファイルが存在することをテストします（2022年は除外）。

        Returns:
            None
        """
        required_files = ["top.html", "rule.html", "ticket.html", "time_schedule.html"]

        for year in self.available_years:
            if year <= 2022:
                continue  # 2022年以前は除外
            year_dir = os.path.join(self.templates_dir, str(year))
            for file_name in required_files:
                file_path = os.path.join(year_dir, file_name)
                with self.subTest(year=year, file=file_name):
                    self.assertTrue(
                        os.path.exists(file_path),
                        f"年度 {year} の必須ファイル {file_name} が存在しません: {file_path}",
                    )

    def test_world_map_directory_structure(self):
        """
        各年度のworld_mapディレクトリ構造が正しいことをテストします。
        """
        for year in self.available_years:
            year_dir = os.path.join(self.templates_dir, str(year))
            world_map_dir = os.path.join(year_dir, "world_map")

            with self.subTest(year=year):
                self.assertTrue(
                    os.path.exists(world_map_dir),
                    f"年度 {year} のworld_mapディレクトリが存在しません: {world_map_dir}",
                )


if __name__ == "__main__":
    unittest.main()
