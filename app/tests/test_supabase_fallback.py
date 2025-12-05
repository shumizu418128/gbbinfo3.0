"""
Supabaseフォールバック取得のテストモジュール。

python -m pytest app/tests/test_supabase_fallback.py -v
"""

import unittest
from unittest.mock import patch

from app.main import app
from app.models.supabase_client import supabase_service
from app.models.supabase_fallback import supabase_fallback
from app.views.beatboxer_tavily_search import get_beatboxer_name


class DictCache:
    """シンプルな辞書キャッシュ（flask_cacheモック用）。"""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, timeout=None):
        self.store[key] = value


class FailingQuery:
    """Supabaseクエリモック: executeで常に例外を送出し、フォールバックを誘発する。"""

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def gt(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lt(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def neq(self, *_args, **_kwargs):
        return self

    def like(self, *_args, **_kwargs):
        return self

    def ilike(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def contains(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    @property
    def not_(self):
        # not_.like / not_.ilike / not_.is_ を満たすため自身を返す
        return self

    def is_(self, *_args, **_kwargs):
        return self

    def execute(self):
        raise Exception("force supabase failure")


class FailingClient:
    """Supabaseクライアントモック: table() で FailingQuery を返す。"""

    def __init__(self):
        self.query = FailingQuery()

    def table(self, *_args, **_kwargs):
        return self.query


class SupabaseFallbackTestCase(unittest.TestCase):
    """Supabaseフォールバック動作を検証するテストケース。"""

    def setUp(self):
        """テスト前準備。"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # flask_cache を簡易キャッシュに差し替え
        self.cache = DictCache()
        self.cache_patcher = patch("app.main.flask_cache", self.cache)
        self.cache_patcher.start()

        # Supabaseクライアントをフォールバック誘発用のモックに差し替え
        self.failing_client = FailingClient()
        supabase_service._admin_client = self.failing_client
        supabase_service._read_only_client = self.failing_client

    def tearDown(self):
        """テスト後のクリーンアップ。"""
        self.cache_patcher.stop()
        self.app_context.pop()

    def test_get_data_fallback_no_join(self):
        """JOINなしでバックアップCSVからフィルタ済みデータを取得できることを確認する。"""
        data = supabase_fallback.get_data_fallback(
            table="Year",
            columns=["year", "categories"],
            order_by="year",
            join_tables=None,
            filters={"year": 2014},
            pandas=False,
            timeout=0,
            raise_error=True,
        )

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["year"], 2014)
        self.assertIn("categories", data[0])

    def test_get_data_fallback_with_join_country(self):
        """JOINあり（Country）でバックアップCSVを結合できることを確認する。"""
        data = supabase_fallback.get_data_fallback(
            table="Participant",
            columns=["id", "name", "iso_code"],
            order_by=None,
            join_tables={"Country": ["names", "iso_alpha2"]},
            filters={"year": 2014},
            pandas=False,
            timeout=0,
            raise_error=True,
        )

        self.assertGreater(len(data), 0)
        first = data[0]
        self.assertIn("Country", first)
        self.assertIsInstance(first["Country"], dict)
        self.assertIn("iso_code", first)
        # Country側の結合結果にも列が入っていること
        self.assertTrue("names" in first["Country"] or "iso_alpha2" in first["Country"])

    def test_view_helper_fallback_without_join(self):
        """ビュー側ヘルパーからのget_data呼び出しでフォールバックが機能すること（JOINなし）。"""
        name = get_beatboxer_name(1573, mode="single")
        self.assertEqual(name, "SLIZZER")

    def test_participants_view_fallback_with_join(self):
        """participants_view経由のJOINあり取得でフォールバックが機能し、200が返ることを確認する。"""
        with self.client.session_transaction() as sess:
            sess["language"] = "en"

        resp = self.client.get(
            "/2014/participants?category=Loopstation&ticket_class=all&cancel=show"
        )

        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        # 参加者名（フォールバック側のデータ）が描画されていることを緩く確認
        self.assertIn("LOOPSTATION", html.upper())


if __name__ == "__main__":
    unittest.main()
