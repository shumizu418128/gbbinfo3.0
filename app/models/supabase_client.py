"""
Supabaseクライアント設定
SupabaseとのAPIやりとり用
"""

import hashlib
import json
import os
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import Client, create_client

from app.util.filter_eq import Operator

ALL_DATA = "*"
MINUTE = 60

# ここに書かないと読み込みタイミングが遅くなってエラーになる
load_dotenv()


class SupabaseService:
    """Supabaseとのやり取りを管理するサービスクラス

    SupabaseのAPIを利用して、データベース操作（取得）を行うためのサービスクラス。
    取得以外の操作は行わない。

    Attributes:
        _client (Optional[Client]): Supabaseクライアントのインスタンス（管理者権限用）
    """

    def __init__(self):
        """SupabaseServiceクラスの初期化

        インスタンス生成時にSupabaseクライアントを初期化する（遅延初期化）。
        また、必要な環境変数が設定されているかを先にチェックする。
        """
        # 先に環境変数の存在をまとめてチェックし、足りないものをすべてエラーで出す
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        missing_envs = []
        if not supabase_url:
            missing_envs.append("SUPABASE_URL")
        if not supabase_anon_key:
            missing_envs.append("SUPABASE_ANON_KEY")
        if not supabase_service_role_key:
            missing_envs.append("SUPABASE_SERVICE_ROLE_KEY")
        if missing_envs:
            raise ValueError(f"以下の環境変数が必要です: {', '.join(missing_envs)}")

        self._read_only_client: Optional[Client] = None
        self._admin_client: Optional[Client] = None

    @property
    def read_only_client(self) -> Client:
        """Supabaseクライアントのインスタンスを取得（読み取り専用）

        Returns:
            Client: Supabaseクライアントのインスタンス

        Raises:
            ValueError: 環境変数SUPABASE_URLまたはSUPABASE_ANON_KEYが設定されていない場合
        """
        if self._read_only_client is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")

            self._read_only_client = create_client(supabase_url, supabase_key)

        return self._read_only_client

    @read_only_client.setter
    def read_only_client(self, value: Optional[Client]):
        """Supabaseクライアントのインスタンスを設定（読み取り専用）

        主にテスト用途で使用されます。

        Args:
            value: 設定するSupabaseクライアントのインスタンス
        """
        self._read_only_client = value

    @property
    def admin_client(self) -> Client:
        """Supabaseクライアントのインスタンスを取得（管理者権限）

        Returns:
            Client: Supabaseクライアントのインスタンス

        Raises:
            ValueError: 環境変数SUPABASE_URLまたはSUPABASE_SERVICE_ROLE_KEYが設定されていない場合
        """
        if self._admin_client is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            self._admin_client = create_client(supabase_url, supabase_key)

        return self._admin_client

    def _apply_filter(self, query, field: str, operator: str, value):
        """フィルター条件をクエリに適用

        Args:
            query: Supabaseクエリオブジェクト
            field (str): フィルター対象のフィールド名
            operator (str): 演算子（gt, gte, lt, lte, neq, like, ilike, is, is_not, in など）
            value: フィルター値

        Returns:
            適用後のクエリオブジェクト
        """
        if operator == Operator.GREATER_THAN:
            return query.gt(field, value)
        elif operator == Operator.GREATER_THAN_OR_EQUAL_TO:
            return query.gte(field, value)
        elif operator == Operator.LESS_THAN:
            return query.lt(field, value)
        elif operator == Operator.LESS_THAN_OR_EQUAL_TO:
            return query.lte(field, value)
        elif operator == Operator.NOT_EQUAL:
            return query.neq(field, value)
        elif operator == Operator.LIKE:
            return query.like(field, value)
        elif operator == Operator.ILIKE:
            return query.ilike(field, value)
        elif operator == Operator.NOT_LIKE:
            return query.not_.like(field, value)
        elif operator == Operator.NOT_ILIKE:
            return query.not_.ilike(field, value)
        elif operator == Operator.IS:
            return query.is_(field, value)
        elif operator == Operator.IS_NOT:
            return query.not_.is_(field, value)
        elif operator == Operator.IN_:
            return query.in_(field, value)
        elif operator == Operator.CONTAINS:
            return query.contains(field, value)
        else:
            # 未対応の演算子の場合は等価条件にフォールバック
            return query.eq(field, value)

    def _generate_cache_key(
        self,
        table: str,
        columns: Optional[list] = None,
        order_by: str | list[str] = None,
        join_tables: Optional[dict] = None,
        filters: Optional[dict] = None,
        **filters_eq,
    ) -> str:
        """キャッシュキーを生成する

        Args:
            各get_dataメソッドのパラメータと同じ

        Returns:
            str: ハッシュ化されたキャッシュキー
        """

        # パラメータを辞書にまとめる
        def make_json_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_json_serializable(obj[k]) for k in sorted(obj)}
            elif isinstance(obj, list):
                return [make_json_serializable(v) for v in obj]
            elif isinstance(obj, set):
                return sorted(list(obj))
            else:
                return obj

        params = {
            "table": table,
            "columns": sorted(columns) if columns else None,
            "order_by": order_by,
            "join_tables": make_json_serializable(join_tables),
            "filters": make_json_serializable(filters),
            "filters_eq": make_json_serializable(dict(sorted(filters_eq.items()))),
        }

        # JSON文字列に変換してハッシュ化
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        cache_key = hashlib.md5(params_str.encode("utf-8")).hexdigest()
        return f"supabase_data_{cache_key}"

    def get_data(
        self,
        table: str,
        columns: Optional[list] = None,
        order_by: str = None,
        join_tables: Optional[dict] = None,
        filters: Optional[dict] = None,
        pandas: bool = False,
        **filters_eq,
    ):
        """テーブルからデータを取得（キャッシュ機能付き）

        Args:
            table (str): 取得対象のテーブル名
            columns (Optional[list]): 取得するカラムのリスト。Noneの場合は全てのカラムを取得
            order_by (str, optional): 並び替え対象のカラム名。降順の場合は'-'を先頭につける。
            join_tables (Optional[dict]): JOINするテーブルの設定
                例: {"Country": ["names", "iso_code"], "Category": ["name"]}
                または {"Country": "*", "Category": "*"} で全カラム取得
                ネストしたJOINも可能: {"ParticipantMember": ["name", "Country(names)"]}
                これにより ParticipantMember.iso_code -> Country.names の二重JOINが実現
            filters (Optional[dict]): 高度なフィルター条件
                例: {
                    "age__gt": 18,  # age > 18
                    "name__like": "%John%",  # name LIKE '%John%'
                    "status__neq": "inactive",  # status != 'inactive'
                    "categories__is_not": None,  # categories IS NOT NULL
                    "tags__in": ["tag1", "tag2"],  # tags IN ('tag1', 'tag2')
                }
            pandas (bool): データをpandasのDataFrameとして取得するかどうか
            **filters_eq: 等価フィルター条件（従来の形式、キー=値）

        Returns:
            List[Dict[str, Any]]: 取得したデータのリスト。エラー時は空リスト

        Example:
            >>> service = SupabaseService()
            >>> # 従来の方法（等価条件のみ）
            >>> data = service.get_data("users", columns=["id", "name"], status="active")
            >>> # 高度なフィルター
            >>> data = service.get_data("users", filters={"age__gt": 18, "name__like": "%John%"})
            >>> # categoriesがNULLでないものを取得
            >>> data = service.get_data("Year", filters={"categories__is_not": None})
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        # キャッシュキーを生成
        cache_key = self._generate_cache_key(
            table=table,
            columns=columns,
            order_by=order_by,
            join_tables=join_tables,
            filters=filters,
            **filters_eq,
        )

        # キャッシュから取得を試行 あるなら返す
        cached_data = flask_cache.get(cache_key)
        if cached_data is not None:
            if pandas:
                return pd.DataFrame(cached_data, index=None)
            else:
                return cached_data

        # カラム指定の構築
        if join_tables:
            # JOINありの場合
            select_parts = []

            # メインテーブルのカラム
            if columns is None:
                select_parts.append(ALL_DATA)
            else:
                select_parts.extend(columns)

            # JOINテーブルのカラム
            for join_table, join_columns in join_tables.items():
                # すべてのカラムを取得
                if join_columns == ALL_DATA:
                    select_parts.append(f"{join_table}({ALL_DATA})")

                # カラムリストが指定されている場合
                elif isinstance(join_columns, list):
                    # ネストしたJOINをサポート
                    processed_columns = []
                    for column in join_columns:
                        if "(" in column and ")" in column:
                            # ネストしたJOIN（例：Country(names)）をそのまま追加
                            processed_columns.append(column)
                        else:
                            # 通常のカラム名
                            processed_columns.append(column)
                    join_columns_str = ",".join(processed_columns)
                    select_parts.append(f"{join_table}({join_columns_str})")

                # カラム名が指定されている場合
                else:
                    select_parts.append(f"{join_table}({join_columns})")

            columns_str = ",".join(select_parts)

        else:
            # JOINなしの場合（従来の処理）
            if columns is None:
                columns_str = ALL_DATA
            else:
                columns_str = ",".join(columns)

        # クエリを構築
        query = self.read_only_client.table(table).select(columns_str)

        # 高度なフィルター条件を適用
        if filters:
            for filter_key, value in filters.items():
                if "__" in filter_key:
                    field, operator = filter_key.split("__", 1)
                    query = self._apply_filter(query, field, operator, value)
                else:
                    # __がない場合は等価条件として扱う
                    query = query.eq(filter_key, value)

        # 等価フィルター条件を適用（従来の形式）
        for key, value in filters_eq.items():
            query = query.eq(key, value)

        # 並び替え条件を適用
        if order_by:
            if order_by.startswith("-"):
                query = query.order(order_by[1:], desc=True)
            else:
                query = query.order(order_by)

        # 用意したqueryを実行し、データを取得
        response = query.execute()

        # 取得したデータをキャッシュに保存
        flask_cache.set(cache_key, response.data, timeout=15 * MINUTE)

        if pandas:
            return pd.DataFrame(response.data, index=None)
        else:
            return response.data

    # 以下、Tavilyのデータを管理するメソッド

    def get_tavily_data(self, cache_key: str):
        """Tavilyのデータを取得する"""
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        search_result = flask_cache.get(cache_key)
        if search_result is not None:
            return search_result

        query = self.admin_client.table("Tavily").select()
        query = query.eq("cache_key", cache_key)
        response = query.execute()

        if len(response.data) == 0:
            return []

        response_results = response.data[0]["search_results"]

        if isinstance(response_results, list):
            flask_cache.set(cache_key, response_results, timeout=None)
            return response_results
        else:
            flask_cache.set(cache_key, json.loads(response_results), timeout=None)
            return json.loads(response_results)

    def insert_tavily_data(self, cache_key: str, search_result: dict):
        """Tavily 検索結果を保存する（重複は安全に吸収）

        Args:
            cache_key (str): 一意キー。
            search_result (dict): Tavily の検索結果。

        Notes:
            - まずアプリ内キャッシュへ保存します（即応答のため）。
            - DB 書き込みは一意制約違反(23505)のみ握りつぶし、既存レコードを更新します。
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        # 即時にアプリキャッシュへ保存（DB 失敗でもレスポンスは可能）
        flask_cache.set(cache_key, search_result, timeout=None)

        data = {
            "cache_key": cache_key,
            "search_results": json.dumps(search_result),
        }

        try:
            # 競合が無ければそのまま insert
            self.admin_client.table("Tavily").insert(data).execute()
        except APIError as e:
            # 同時実行時などの重複キーは無視しつつ中身を最新に更新
            if getattr(e, "code", None) == "23505":
                self.admin_client.table("Tavily").update(
                    {"search_results": json.dumps(search_result)}
                ).eq("cache_key", cache_key).execute()
            else:
                # それ以外のDBエラーは再送出
                raise


# グローバルインスタンス
supabase_service = SupabaseService()
