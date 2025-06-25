"""
Supabaseクライアント設定
SupabaseとのAPIやりとり用
"""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseService:
    """Supabaseとのやり取りを管理するサービスクラス"""

    def __init__(self):
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Supabaseクライアントのインスタンスを取得"""
        if self._client is None:
            load_dotenv()
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URLとSUPABASE_ANON_KEYの環境変数が必要です")

            self._client = create_client(supabase_url, supabase_key)
            print(self._client)

        return self._client

    def get_table_data(self, table_name: str, **filters) -> List[Dict[str, Any]]:
        """テーブルからデータを取得"""
        try:
            query = self.client.table(table_name).select("*")

            # フィルター条件を適用
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()
            return response.data
        except Exception as e:
            print(f"データ取得エラー: {e}")
            return []

    def insert_data(
        self, table_name: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """テーブルにデータを挿入"""
        try:
            response = self.client.table(table_name).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"データ挿入エラー: {e}")
            return None

    def update_data(
        self, table_name: str, data: Dict[str, Any], **filters
    ) -> Optional[List[Dict[str, Any]]]:
        """テーブルのデータを更新"""
        try:
            query = self.client.table(table_name).update(data)

            # フィルター条件を適用
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()
            return response.data
        except Exception as e:
            print(f"データ更新エラー: {e}")
            return None

    def delete_data(self, table_name: str, **filters) -> bool:
        """テーブルからデータを削除"""
        try:
            query = self.client.table(table_name).delete()

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
