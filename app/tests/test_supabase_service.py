"""
Flask アプリケーションのSupabaseサービスのテストモジュール

python -m pytest app/tests/test_supabase_service.py -v
"""

import os
import unittest
from unittest.mock import Mock, patch


# Supabaseサービスをモックしてからapp.mainをインポート
with patch("app.context_processors.supabase_service") as mock_supabase:
    mock_supabase.get_data.return_value = [{"year": 2025}]
    from app.main import app

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


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
            # 読み取り用クエリモックを準備
            query = self.QueryMock()
            query.response_data = [{"id": 1, "name": "Alice"}]

            with patch(
                "app.models.supabase_client.create_client"
            ) as mock_create_client:
                mock_create_client.return_value = self.FakeClient(query)

                service = SupabaseService()
                # クライアントプロパティをリセットしてモックが使われるようにする
                service._read_only_client = None

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
            query = self.QueryMock()
            query.response_data = [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]

            with patch(
                "app.models.supabase_client.create_client"
            ) as mock_create_client:
                mock_create_client.return_value = self.FakeClient(query)

                service = SupabaseService()
                # クライアントプロパティをリセットしてモックが使われるようにする
                service._read_only_client = None

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

        service = SupabaseService()

        # 初回アクセス - クライアントが作成される
        with patch("app.models.supabase_client.create_client") as mock_create_client:
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            client1 = service.read_only_client
            self.assertEqual(client1, mock_client)
            mock_create_client.assert_called_once_with(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY")
            )

        # 2回目のアクセス - キャッシュされたクライアントが返される
        client2 = service.read_only_client
        self.assertEqual(client2, mock_client)

    def test_admin_client_property_getter(self):
        """admin_client propertyのgetter動作を検証する。"""
        from app.models.supabase_client import SupabaseService

        service = SupabaseService()

        # 初回アクセス - 管理者クライアントが作成される
        with patch("app.models.supabase_client.create_client") as mock_create_client:
            mock_client = Mock()
            mock_create_client.return_value = mock_client

            client1 = service.admin_client
            self.assertEqual(client1, mock_client)
            mock_create_client.assert_called_once_with(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            )

        # 2回目のアクセス - キャッシュされたクライアントが返される
        client2 = service.admin_client
        self.assertEqual(client2, mock_client)

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

        service = SupabaseService()

        # インスタンス変数が正しく初期化されていることを確認
        self.assertIsNone(service._read_only_client)
        self.assertIsNone(service._admin_client)

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
