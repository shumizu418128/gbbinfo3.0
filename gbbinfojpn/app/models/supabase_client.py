"""
Supabaseクライアント設定
SupabaseとのAPIやりとり用
"""

import hashlib
import json
import os
from typing import Optional

from django.core.cache import cache
from supabase import Client, create_client

from gbbinfojpn.common.filter_eq import Operator

ALL_DATA = "*"
MINUTE = 60


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
        """
        self._client: Optional[Client] = None

    @property
    def read_only_client(self) -> Client:
        """Supabaseクライアントのインスタンスを取得（読み取り専用）

        Returns:
            Client: Supabaseクライアントのインスタンス

        Raises:
            ValueError: 環境変数SUPABASE_URLまたはSUPABASE_ANON_KEYが設定されていない場合
        """
        if self._client is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URLとSUPABASE_ANON_KEYの環境変数が必要です")

            self._client = create_client(supabase_url, supabase_key)

        return self._client

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
        order_by: str = None,
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
        params = {
            "table": table,
            "columns": sorted(columns) if columns else None,
            "order_by": order_by,
            "join_tables": join_tables,
            "filters": filters,
            "filters_eq": dict(sorted(filters_eq.items())),
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
            filters (Optional[dict]): 高度なフィルター条件
                例: {
                    "age__gt": 18,  # age > 18
                    "name__like": "%John%",  # name LIKE '%John%'
                    "status__neq": "inactive",  # status != 'inactive'
                    "categories__is_not": None,  # categories IS NOT NULL
                    "tags__in": ["tag1", "tag2"],  # tags IN ('tag1', 'tag2')
                }
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
        cached_data = cache.get(cache_key)
        if cached_data is not None:
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
                    join_columns_str = ",".join(join_columns)
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
        cache.set(cache_key, response.data, timeout=15 * MINUTE)

        return response.data


# グローバルインスタンス
supabase_service = SupabaseService()
