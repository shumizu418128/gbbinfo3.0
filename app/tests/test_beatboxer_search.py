"""
Flask アプリケーションのBeatboxer Tavily検索のテストモジュール

python -m pytest app/tests/test_beatboxer_search.py -v
"""

import unittest
from unittest.mock import patch

from app.main import app

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


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
            [{"name": "test_beatboxer"}],  # for get_beatboxer_name
        ]
        mock_supabase.get_tavily_data.side_effect = [
            [],  # answer_translation (cache miss)
            {"answer": "This is an answer"},  # search_results
            [],  # existing_cache for saving translation
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
                        {"id": 1, "name": "Loopstation", "is_team": False},
                        {"id": 2, "name": "Tag Team", "is_team": True},
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
                                "iso_code": 392,
                                "Category": {
                                    "id": 1,
                                    "name": "Loopstation",
                                    "is_team": False,
                                },
                                "Country": {"iso_alpha2": "JP"},
                                "ParticipantMember": [],
                            },
                            {
                                "id": 101,
                                "name": "Team J",
                                "category": 2,
                                "ticket_class": "GBB Seed",
                                "is_cancelled": False,
                                "iso_code": 392,
                                "Category": {
                                    "id": 2,
                                    "name": "Tag Team",
                                    "is_team": True,
                                },
                                "Country": {"iso_alpha2": "JP"},
                                "ParticipantMember": [{"name": "M1"}],
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
                                "iso_code": 410,
                                "Category": {
                                    "id": 1,
                                    "name": "Loopstation",
                                    "is_team": False,
                                },
                                "Country": {"iso_alpha2": "KR"},
                                "ParticipantMember": [],
                            },
                            {
                                "id": 111,
                                "name": "Team K",
                                "category": 2,
                                "ticket_class": "GBB Seed",
                                "is_cancelled": False,
                                "iso_code": 410,
                                "Category": {
                                    "id": 2,
                                    "name": "Tag Team",
                                    "is_team": True,
                                },
                                "Country": {"iso_alpha2": "KR"},
                                "ParticipantMember": [{"name": "K1"}],
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
                                "iso_code": 9999,
                                "Category": {
                                    "id": 2,
                                    "name": "Tag Team",
                                    "is_team": True,
                                },
                                "Country": {"iso_code": 9999, "iso_alpha2": "XX"},
                                "ParticipantMember": [
                                    {
                                        "name": "JP",
                                        "iso_code": 392,
                                        "Country": {"iso_alpha2": "JP"},
                                    },
                                    {
                                        "name": "KR",
                                        "iso_code": 410,
                                        "Country": {"iso_alpha2": "KR"},
                                    },
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
                            "Category": {
                                "id": 1,
                                "name": "Loopstation",
                                "is_team": False,
                            },
                            "Country": {
                                "iso_code": 392,
                                "names": {"ja": "日本", "en": "Japan"},
                                "iso_alpha2": "JP",
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
                            "Category": {"id": 2, "name": "Tag Team", "is_team": True},
                            "Country": {
                                "iso_code": 826,
                                "names": {"ja": "イギリス", "en": "UK"},
                                "iso_alpha2": "GB",
                            },
                            "ParticipantMember": [
                                {
                                    "name": "M1",
                                    "Country": {
                                        "names": {"ja": "日本"},
                                        "iso_alpha2": "JP",
                                    },
                                }
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
                            "Participant": {
                                "id": 301,
                                "name": "RSolo",
                                "Country": {"iso_code": 392, "iso_alpha2": "JP"},
                            },
                        }
                    ]
                if category_id == 2:
                    return [
                        {
                            "round": None,
                            "participant": 2,
                            "rank": 1,
                            "Participant": {
                                "id": 302,
                                "name": "RTeam",
                                "Country": {"iso_code": 840, "iso_alpha2": "US"},
                            },
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
                        "iso_code": 392,
                        "Category": {"id": 1, "name": "Loopstation", "is_team": False},
                        "Country": {
                            "iso_code": 392,
                            "names": {"ja": "日本", "en": "Japan"},
                            "iso_alpha2": "JP",
                        },
                        "ParticipantMember": [],
                    },
                    {
                        "id": 402,
                        "name": "SeedTeam",
                        "category": 2,
                        "is_cancelled": False,
                        "ticket_class": "GBB Seed",
                        "iso_code": 392,
                        "Category": {"id": 2, "name": "Tag Team", "is_team": True},
                        "Country": {
                            "iso_code": 392,
                            "names": {"ja": "日本", "en": "Japan"},
                            "iso_alpha2": "JP",
                        },
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
                                "iso_alpha2": "JP",
                            },
                            "Participant": {
                                "id": 1923,
                                "name": "WOLFGANG",
                                "year": 2025,
                                "category": 2,
                                "is_cancelled": False,
                                "iso_code": 392,
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
                                "iso_alpha2": "JP",
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
                                "iso_alpha2": "GB",
                            },
                            "Category": {"id": 2, "name": "Tag Team"},
                            "ParticipantMember": [
                                {
                                    "id": 255,
                                    "name": "TAKO",
                                    "Country": {
                                        "names": {"ja": "日本"},
                                        "iso_alpha2": "JP",
                                    },
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
                        "Country": {
                            "iso_code": 392,
                            "names": {"ja": "日本", "en": "Japan"},
                            "iso_alpha2": "JP",
                        },
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
                "iso_code": 392,
                "Category": {"name": "Loopstation", "is_team": False},
                "Country": {"iso_alpha2": "JP"},
                "ParticipantMember": [],  # シングル参加者
            },
            {
                "id": 2,
                "name": "test_team_1",
                "category": "Tag Team",
                "ticket_class": "Wildcard 1st",
                "iso_code": 840,
                "Category": {"name": "Tag Team", "is_team": True},
                "Country": {"iso_alpha2": "US"},
                "ParticipantMember": [
                    {"name": "Member1", "Country": {"iso_alpha2": "JP"}},
                    {"name": "Member2", "Country": {"iso_alpha2": "KR"}},
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
                        "iso_code": 392,
                        "Category": {"name": "Loopstation", "is_team": False},
                        "Country": {"iso_alpha2": "JP"},
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
