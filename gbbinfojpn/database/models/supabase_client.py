"""
Supabaseクライアント設定
SupabaseとのAPIやりとり用
"""

import os
from typing import Optional

from supabase import Client, create_client

from gbbinfojpn import settings

ALL_DATA = "*"


class SupabaseService:
    """Supabaseとのやり取りを管理するサービスクラス"""

    def __init__(self):
        """SupabaseServiceクラスの初期化"""
        self._client: Optional[Client] = None

    @property
    def admin_client(self) -> Client:
        """Supabaseクライアントのインスタンスを取得（管理者権限）

        Returns:
            Client: Supabaseクライアントのインスタンス

        Raises:
            ValueError: 環境変数SUPABASE_URLまたはSUPABASE_SERVICE_ROLE_KEYが設定されていない場合
        """
        if self._client is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError(
                    "SUPABASE_URLとSUPABASE_SERVICE_ROLE_KEYの環境変数が必要です"
                )

            self._client = create_client(supabase_url, supabase_key)

        return self._client

    def get_data(
        self,
        table: str,
        columns: Optional[list] = None,
        order_by: str = None,
        **filters,
    ):
        """テーブルからデータを取得

        Args:
            table (str): 取得対象のテーブル名
            columns (Optional[list]): 取得するカラムのリスト。Noneの場合は全てのカラムを取得
            order_by (str, optional): 並び替え対象のカラム名。降順の場合は'-'を先頭につける。
            **filters: フィルター条件（キー=値の形式）

        Returns:
            List[Dict[str, Any]]: 取得したデータのリスト。エラー時は空リスト

        Example:
            >>> service = SupabaseService()
            >>> data = service.get_data("users", columns=["id", "name"], status="active")
            >>> data = service.get_data("users", order_by="-created_at")
        """
        # テーブルを取得、カラムを指定
        if columns is None:
            query = self.admin_client.table(table).select(ALL_DATA)
        else:
            # リストの場合はカンマ区切りの文字列に変換
            columns_str = ",".join(columns)
            query = self.admin_client.table(table).select(columns_str)

        # フィルター条件を適用
        for key, value in filters.items():
            query = query.eq(key, value)

        # 並び替え条件を適用
        if order_by:
            if order_by.startswith("-"):
                query = query.order(order_by[1:], desc=True)
            else:
                query = query.order(order_by)

        # 用意したqueryを実行し、データを取得
        response = query.execute()
        return response.data

    def insert_data(self, table: str, data: dict):
        """テーブルにデータを挿入

        Args:
            table (str): 挿入対象のテーブル名
            data (dict): 挿入するデータ

        Returns:
            Optional[dict]: 挿入されたデータ。エラー時はNone

        Example:
            >>> service = SupabaseService()
            >>> new_user = {"name": "John", "email": "john@example.com"}
            >>> result = service.insert_data("users", new_user)
        """
        response = self.admin_client.table(table).insert(data).execute()
        return response.data[0] if response.data else None

    def update_data(self, table: str, data: dict, order_by: str = None, **filters):
        """テーブルのデータを更新

        Args:
            table (str): 更新対象のテーブル名
            data (dict): 更新するデータ
            order_by (str, optional): 並び替え対象のカラム名。降順の場合は'-'を先頭につける。
            **filters: 更新対象を特定するフィルター条件

        Returns:
            Optional[list[dict]]: 更新されたデータのリスト。エラー時はNone

        Example:
            >>> service = SupabaseService()
            >>> update_data = {"status": "inactive"}
            >>> result = service.update_data("users", update_data, id=123)
            >>> result = service.update_data("users", update_data, order_by="-updated_at", id=123)
        """
        query = self.admin_client.table(table).update(data)

        # フィルター条件を適用
        for key, value in filters.items():
            query = query.eq(key, value)

        # 並び替え条件を適用
        if order_by:
            if order_by.startswith("-"):
                query = query.order(order_by[1:], desc=True)
            else:
                query = query.order(order_by)

        response = query.execute()
        return response.data

    def delete_data(self, table: str, **filters):
        """テーブルからデータを削除
        この処理はADMIN_CLIENTを使用・標準入力による確認が必要

        Args:
            table (str): 削除対象のテーブル名
            **filters: 削除対象を特定するフィルター条件

        Returns:
            bool: 削除が成功した場合はTrue、失敗した場合はFalse

        Note:
            この関数はローカル環境（DEBUG=True）でのみ動作します。
            削除前に確認プロンプトが表示されます。

        Example:
            >>> service = SupabaseService()
            >>> success = service.delete_data("users", id=123)
        """

        # ローカル環境のみ
        if not settings.DEBUG:
            return False

        # データ削除確認
        print(f"delete: {table}, {filters}")
        password = input("***are you sure you want to delete?*** (YES/no): ")
        if password != "YES":
            return False

        query = self.admin_client.table(table).delete()

        # フィルター条件を適用
        for key, value in filters.items():
            query = query.eq(key, value)

        query.execute()
        return True


# グローバルインスタンス
supabase_service = SupabaseService()
