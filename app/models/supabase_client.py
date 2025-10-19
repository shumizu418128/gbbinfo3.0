"""
Supabaseクライアント設定
SupabaseとのAPIやりとり用
"""

import hashlib
import json
import os
import traceback
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import Client, create_client

from app.models.googletrans_client import googletrans_service
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

    # MARK: read only
    @property
    def read_only_client(self) -> Client:
        """Supabaseクライアントのインスタンスを取得（読み取り専用）
        遅延初期化しないとtestでエラーになる

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

    # MARK: admin
    @property
    def admin_client(self) -> Client:
        """Supabaseクライアントのインスタンスを取得（管理者権限）
        遅延初期化しないとtestでエラーになる

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

    # MARK: filter
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

    # MARK: cache key
    def _generate_cache_key(
        self,
        table: str,
        columns: Optional[list] = None,
        order_by: str | list[str] = None,
        join_tables: Optional[dict] = None,
        filters: Optional[dict] = None,
        **filters_eq,
    ) -> str:
        """
        キャッシュキーを生成する内部メソッド。

        Supabaseからデータを取得する際のクエリ条件（テーブル名、カラム、並び順、JOIN、フィルタなど）をもとに
        一意なキャッシュキー（MD5ハッシュ）を生成します。

        Args:
            table (str): 対象テーブル名。
            columns (Optional[list], optional): 取得カラム名リスト。デフォルトはNone。
            order_by (str | list[str], optional): 並び替え条件。デフォルトはNone。
            join_tables (Optional[dict], optional): JOINするテーブル情報。デフォルトはNone。
            filters (Optional[dict], optional): フィルタ条件。デフォルトはNone。
            **filters_eq: その他、等価条件によるフィルタをキーワード引数で指定。

        Returns:
            str: クエリ条件に基づく一意なキャッシュキー文字列。
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

    # MARK: get
    def get_data(
        self,
        table: str,
        columns: Optional[list] = None,
        order_by: str = None,
        join_tables: Optional[dict] = None,
        filters: Optional[dict] = None,
        pandas: bool = False,
        timeout: int = 30 * MINUTE,
        raise_error: bool = False,
        **filters_eq,
    ):
        """
        指定したテーブルからデータを取得するメソッド。

        Args:
            table (str): 取得対象のテーブル名。
            columns (Optional[list], optional): 取得するカラム名のリスト。Noneの場合は全カラムを取得。デフォルトはNone。
            order_by (str, optional): 並び替えに使用するカラム名。デフォルトはNone。
            join_tables (Optional[dict], optional): JOINするテーブルとそのカラムの指定。デフォルトはNone。
            filters (Optional[dict], optional): フィルタ条件を指定する辞書。デフォルトはNone。
            pandas (bool, optional): Trueの場合はpandas.DataFrameで返す。デフォルトはFalse。
            timeout (int, optional): キャッシュの有効期限。デフォルトは30分。
            **filters_eq: その他、等価条件によるフィルタをキーワード引数で指定。

        Returns:
            list[dict] | pandas.DataFrame: 取得したデータのリスト、またはpandas.DataFrame（pandas=Trueの場合）。

        Raises:
            ValueError: テーブル名が指定されていない場合や、取得に失敗した場合に発生。
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
        # なぜかread_onlyの動作が不安定なので、一時的にadmin_clientを使用
        # query = self.read_only_client.table(table).select(columns_str)
        query = self.admin_client.table(table).select(columns_str)

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
        try:
            response = query.execute()
        except Exception as e:
            print("SupabaseClient get_data error:", flush=True)
            traceback.print_exc()
            if raise_error:
                raise e
            if pandas:
                return pd.DataFrame([], index=None)
            return []

        # 取得したデータをキャッシュに保存
        flask_cache.set(cache_key, response.data, timeout=timeout)

        if pandas:
            return pd.DataFrame(response.data, index=None)
        return response.data

    # MARK: ---

    # MARK: tavily get
    def get_tavily_data(
        self, cache_key: str, column: str = "search_results", raise_error: bool = False
    ):
        """
        SupabaseのTavilyテーブルから指定したカラムのデータを取得し、アプリ内キャッシュにも保存するメソッド。

        Args:
            cache_key (str): 取得対象データを一意に識別するためのキー。
            column (str, optional): 取得するカラム名。デフォルトは "search_results"。

        Returns:
            Any: 指定カラムのデータ。データが存在しない場合は空リストを返します。

        Notes:
            - まずアプリ内キャッシュ(flask_cache)からデータを取得します。
            - キャッシュに存在しない場合はSupabaseのTavilyテーブルからデータを取得します。
            - 取得したデータはJSON文字列の場合はデコードし、Noneの場合は空リストに正規化します。
            - 取得したデータはアプリ内キャッシュ(flask_cache)にも保存されます。
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        # 内部キャッシュのみkeyはカラム名を含める
        search_result = flask_cache.get(cache_key + "_" + column)
        if search_result is not None:
            return search_result

        query = (
            self.admin_client.table("Tavily").select(column).eq("cache_key", cache_key)
        )
        try:
            response = query.execute()
        except Exception as e:
            print("SupabaseClient get_tavily_data error:", e, flush=True)
            if raise_error:
                raise e
            return []

        if len(response.data) == 0:
            return []

        row = response.data[0]
        response_results = row.get(column)

        # JSON文字列はデコード、Noneは空リストに正規化
        if isinstance(response_results, str):
            try:
                data = json.loads(response_results)
            except Exception:
                data = []
        else:
            data = response_results if response_results is not None else []

        # キャッシュに保存（内部キャッシュのみkeyはカラム名を含める）
        flask_cache.set(cache_key + "_" + column, data, timeout=0)
        return data

    # MARK: insert
    def insert_tavily_data(self, cache_key: str, search_result: dict):
        """
        Tavilyの検索結果データをSupabaseのTavilyテーブルに挿入し、アプリ内キャッシュにも保存するメソッド。

        Args:
            cache_key (str): 検索結果を一意に識別するためのキー。
            search_result (dict): 挿入する検索結果データ。

        Notes:
            - まずアプリ内キャッシュ(flask_cache)にデータを保存します（DB挿入失敗時もレスポンス可能）。
            - 検索結果はJSON文字列としてSupabaseのTavilyテーブルに保存されます。
            - DB挿入に失敗しても例外は握りつぶします。
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        # 即時にアプリキャッシュへ保存（DB 失敗でもレスポンスは可能）
        flask_cache.set(cache_key + "_search_results", search_result, timeout=0)

        data = {
            "cache_key": cache_key,
            "search_results": search_result,
        }

        # 失敗してもエラーにはしない
        try:
            self.admin_client.table("Tavily").insert(data).execute()
        except APIError:
            pass

    # MARK: update
    def update_translated_answer(self, cache_key: str, translated_answer: dict):
        """
        Tavilyの翻訳済み回答を更新する

        Args:
            cache_key (str): 一意キー（Tavilyデータのキャッシュキー）。
            translated_answer (dict): 翻訳済みの回答データ。

        Notes:
            - SupabaseのTavilyテーブルのanswer_translationカラムを更新します。
            - DB更新に失敗しても例外は握りつぶし、アプリ内キャッシュは必ず最新化します。
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        data = {
            "answer_translation": translated_answer,
        }
        try:
            self.admin_client.table("Tavily").update(data).eq(
                "cache_key", cache_key
            ).execute()
        except APIError:
            # DB失敗は握りつぶす（次回以降で再試行）
            pass
        finally:
            # アプリ内キャッシュを最新化
            flask_cache.set(
                cache_key + "_answer_translation", translated_answer, timeout=0
            )

    # MARK: update country
    def update_country_names(self, add_langs: list[str], remove_langs: list[str]):
        """
        Countryテーブルのnamesカラムを更新する

        Args:
            add_langs (list[str]): 追加する言語コードのリスト
            remove_langs (list[str]): 削除する言語コードのリスト
        """
        # まず各国のnamesカラムを取得
        countries = self.get_data("Country", columns=["iso_code", "names"], pandas=True)

        if countries.empty:
            print("国データの取得に失敗しました", flush=True)
            return

        for index, row in countries.iterrows():
            iso_code = row["iso_code"]
            names = row["names"]
            updated = False

            # 0は出場者未定を表す国コード
            if iso_code == 0:
                for add_language in add_langs:
                    names[add_language] = "-"
                updated = True

            # 9999は複数国籍チームを表す国コード
            if iso_code == 9999:
                continue

            if not isinstance(names, dict):
                print(
                    f"国コード {iso_code} のnamesデータが辞書形式ではありません",
                    flush=True,
                )
                continue

            # 削除
            for remove_language in remove_langs:
                if remove_language in names:
                    names.pop(remove_language)
                    updated = True

            # 追加
            if 0 < iso_code < 9999:
                for add_language in add_langs:
                    translation_result = googletrans_service.translate(
                        text=names["en"], src="en", dest=add_language
                    )
                    names[add_language] = translation_result
                    updated = True

            # 更新されたデータを保存
            if updated:
                try:
                    data = {
                        "names": names,
                    }
                    self.admin_client.table("Country").update(data).eq(
                        "iso_code", iso_code
                    ).execute()
                except Exception as e:
                    print(f"国コード {iso_code} の保存中にエラー: {e}", flush=True)


# グローバルインスタンス
supabase_service = SupabaseService()
