from django.db import models

from .supabase_client import supabase_service


class DatabaseEntry(models.Model):
    """
    ウェブアプリケーション用データモデル
    このモデルはSupabaseデータベースに保存されます
    """

    title = models.CharField(max_length=200, verbose_name="タイトル")
    description = models.TextField(blank=True, verbose_name="説明")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    is_active = models.BooleanField(default=True, verbose_name="有効")

    class Meta:
        verbose_name = "データベースエントリ"
        verbose_name_plural = "データベースエントリ"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @classmethod
    def get_supabase_data(cls, **filters):
        """Supabaseから直接データを取得"""
        return supabase_service.get_table_data("database_databaseentry", **filters)

    def save_to_supabase(self):
        """Supabaseに直接データを保存"""
        data = {
            "title": self.title,
            "description": self.description,
            "is_active": self.is_active,
        }
        return supabase_service.insert_data("database_databaseentry", data)


class TestData(models.Model):
    """
    Supabaseのtestテーブル用モデル
    id, created_at, valueフィールドを持つ
    """

    value = models.TextField(verbose_name="テキスト")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        verbose_name = "テストデータ"
        verbose_name_plural = "テストデータ"
        ordering = ["-created_at"]
        managed = False  # Djangoのマイグレーション管理対象外

    def __str__(self):
        return f"TestData {self.id}: {self.value[:50]}"

    @classmethod
    def get_test_data(cls, **filters):
        """Supabaseのtestテーブルから直接データを取得"""
        return supabase_service.get_table_data("test", **filters)
