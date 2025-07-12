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
            print(self._client)

        return self._client

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
            print(self._client)

        return self._client

    def get_data(self, table_name: str, order_by: str = None, **filters):
        """テーブルからデータを取得
        この処理のみREAD_ONLY_CLIENTを使用

        Args:
            table_name (str): 取得対象のテーブル名
            order_by (str, optional): 並び替え対象のカラム名。降順の場合は'-'を先頭につける。
            **filters: フィルター条件（キー=値の形式）

        Returns:
            List[Dict[str, Any]]: 取得したデータのリスト。エラー時は空リスト

        Example:
            >>> service = SupabaseService()
            >>> data = service.get_table_data("users", status="active")
            >>> data = service.get_table_data("users", order_by="-created_at")
        """
        try:
            query = self.read_only_client.table(table_name).select(ALL_DATA)

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
        except Exception as e:
            print(f"データ取得エラー: {e}")
            return []

    def insert_data(self, table_name: str, data: dict):
        """テーブルにデータを挿入
        この処理はADMIN_CLIENTを使用

        Args:
            table_name (str): 挿入対象のテーブル名
            data (dict): 挿入するデータ

        Returns:
            Optional[dict]: 挿入されたデータ。エラー時はNone

        Example:
            >>> service = SupabaseService()
            >>> new_user = {"name": "John", "email": "john@example.com"}
            >>> result = service.insert_data("users", new_user)
        """
        try:
            response = self.admin_client.table(table_name).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"データ挿入エラー: {e}")
            return None

    def update_data(self, table_name: str, data: dict, order_by: str = None, **filters):
        """テーブルのデータを更新
        この処理はADMIN_CLIENTを使用

        Args:
            table_name (str): 更新対象のテーブル名
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
        try:
            query = self.admin_client.table(table_name).update(data)

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
        except Exception as e:
            print(f"データ更新エラー: {e}")
            return None

    def delete_data(self, table_name: str, **filters):
        """テーブルからデータを削除
        この処理はADMIN_CLIENTを使用・標準入力による確認が必要

        Args:
            table_name (str): 削除対象のテーブル名
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
        print(f"delete: {table_name}, {filters}")
        password = input("***are you sure you want to delete?*** (YES/no): ")
        if password != "YES":
            return False

        try:
            query = self.admin_client.table(table_name).delete()

            # フィルター条件を適用
            for key, value in filters.items():
                query = query.eq(key, value)

            query.execute()
            return True
        except Exception as e:
            print(f"データ削除エラー: {e}")
            return False


# グローバルインスタンス
supabase_service = SupabaseService()
