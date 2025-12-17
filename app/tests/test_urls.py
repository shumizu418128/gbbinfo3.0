"""
Flask アプリケーションのURLパターンのテストモジュール

python -m pytest app/tests/test_urls.py -v
"""

import os
import unittest
from unittest.mock import patch

from app.config.config import LANGUAGE_CHOICES

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

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


def create_country_names_mock(country_name_en="Japan"):
    """
    configから取得した言語キーを使用してcountry.namesのモックデータを生成する。

    Args:
        country_name_en (str): 'en'キーに対応する値（デフォルト: "Japan"）。
                               world_map_viewでファイル名として使用されるため、
                               実際のファイル名と一致させる必要がある。

    Returns:
        dict: すべてのサポート言語をキーとして持つ辞書。
              'en'キーには指定されたcountry_name_enが設定され、
              その他のキーには適当な文字列（"Country_{lang_code}"形式）が設定される。
    """
    names = {code: f"Country_{code}" for code, _ in LANGUAGE_CHOICES}
    names["en"] = country_name_en  # world_map_viewでファイル名として使用される
    return names


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
                        "Category": {"name": "Solo", "is_team": False},
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
                                "names": create_country_names_mock(),
                                "iso_alpha2": "JP",
                            }
                        ]
                    )
                return [
                    {
                        "iso_code": 392,
                        "latitude": 35.0,
                        "longitude": 139.0,
                        "names": create_country_names_mock(),
                        "iso_alpha2": "JP",
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
                        "iso_code": 392,
                        "Category": {"id": 1, "name": "Solo", "is_team": False},
                        "Country": {
                            "iso_code": 392,
                            "names": create_country_names_mock(),
                            "iso_alpha2": "JP",
                        },
                        "ParticipantMember": [],
                    }
                ]
            return []

        mock_rule_supabase.get_data.side_effect = rule_get_data_side_effect

        # participants内のSupabase呼び出しモック
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
                        {"id": 1, "name": "Loopstation", "is_team": False},
                        {"id": 2, "name": "Solo", "is_team": False},
                    ]
                )
            if table == "Participant":
                # 日本の出場者データ（iso_code=392）
                if filters.get("iso_code") == 392:
                    return [
                        {
                            "id": 1,
                            "name": "ALPHA",
                            "category": 1,
                            "ticket_class": "GBB Seed",
                            "is_cancelled": False,
                            "iso_code": 392,
                            "Category": {
                                "id": 1,
                                "name": "Loopstation",
                                "is_team": False,
                            },
                            "Country": {
                                "iso_code": 392,
                                "iso_alpha2": "JP",
                            },
                            "ParticipantMember": [],
                        }
                    ]
                # 韓国の出場者データ（iso_code=410）
                elif filters.get("iso_code") == 410:
                    return [
                        {
                            "id": 2,
                            "name": "BIGMAN",
                            "category": 2,
                            "ticket_class": "GBB Seed",
                            "is_cancelled": False,
                            "iso_code": 410,
                            "Category": {"id": 2, "name": "Solo", "is_team": False},
                            "Country": {
                                "iso_code": 410,
                                "iso_alpha2": "KR",
                            },
                            "ParticipantMember": [],
                        }
                    ]
                # 多国籍チームデータ（iso_code=9999）
                elif filters.get("iso_code") == 9999:
                    return [
                        {
                            "id": 100,
                            "name": "MULTINATIONAL TEAM",
                            "category": 1,
                            "ticket_class": "GBB Seed",
                            "is_cancelled": False,
                            "Category": {
                                "id": 1,
                                "name": "Loopstation",
                                "is_team": True,
                            },
                            "ParticipantMember": [
                                {
                                    "name": "Member from Japan",
                                    "iso_code": 392,
                                    "Country": {"iso_alpha2": "JP"},
                                },
                                {
                                    "name": "Member from Korea",
                                    "iso_code": 410,
                                    "Country": {"iso_alpha2": "KR"},
                                },
                            ],
                            "Country": {
                                "iso_code": 9999,
                            },
                        }
                    ]
                # デフォルトの出場者データ
                return [
                    {
                        "id": 1,
                        "name": "ALPHA",
                        "category": 1,
                        "ticket_class": "GBB Seed",
                        "is_cancelled": False,
                        "iso_code": 392,
                        "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                        "Country": {
                            "iso_code": 392,
                            "names": create_country_names_mock(),
                            "iso_alpha2": "JP",
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
            ("/participant_detail/2064/single", "出場者詳細 JUNNO"),
            ("/participant_detail/255/team_member", "出場者詳細 TAKO"),
            ("/participant_detail/1923/team", "出場者詳細 WOLFGANG"),
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

        # デフォルト言語を日本語に設定
        lang = "ja"
        for url, description in test_cases:
            with self.subTest(url=url, description=description):
                # セッションに言語を設定しておく
                with self.client.session_transaction() as sess:
                    sess["language"] = lang
                response = self.client.get(url)

                # 200-399の範囲のステータスコードまたは、レスポンスが存在することを確認
                self.assertTrue(
                    response.status_code in range(200, 400),
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
        # config.pyからサポートされている言語コードのリストを取得
        from app.config.config import LANGUAGE_CHOICES

        # 日本語以外の言語のみを対象とする（日本語はデフォルト言語なので翻訳ファイルが不要）
        supported_languages = [code for code, _ in LANGUAGE_CHOICES if code != "ja"]

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
                        {"id": 1, "name": "Loopstation", "is_team": False},
                        {"id": 2, "name": "Solo", "is_team": False},
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
                        "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                        "Country": {
                            "iso_code": 392,
                            "names": create_country_names_mock(),
                            "iso_alpha2": "JP",
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
                url = f"/{lang}/2025/participants?category=Loopstation&ticket_class=all&cancel=show"
                # セッションに言語を設定してリクエストを行う
                with self.client.session_transaction() as sess:
                    sess["language"] = lang
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
        # config.pyの言語設定を取得
        from app.config.config import LANGUAGE_CHOICES

        main_languages = set([code for code, _ in LANGUAGE_CHOICES if code != "ja"])

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

        self.assertEqual(
            main_languages,
            translation_folders,
            msg=f"main.pyとtranslationsフォルダの言語設定が一致しません。\n"
            f"main.py(jaを除く): {sorted(main_languages)}\n"
            f"translationsフォルダ: {sorted(translation_folders)}\n"
            f"差分: {main_languages.symmetric_difference(translation_folders)}",
        )
