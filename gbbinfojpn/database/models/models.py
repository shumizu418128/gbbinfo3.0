from django.db import models

from gbbinfojpn import settings

from .supabase_client import supabase_service
from .validators import validate_language_keys


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


class Country(models.Model):
    """国情報テーブル"""

    iso_code = models.IntegerField(unique=True, help_text="ISO国コード")
    latitude = models.DecimalField(max_digits=8, decimal_places=6, help_text="緯度")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="経度")
    names = models.JSONField(
        help_text="多言語名称 {en: 'Japan', ja: '日本', ...}",
        validators=[lambda value: validate_language_keys(value, settings.LANGUAGES)],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "countries"
        indexes = [
            models.Index(fields=["iso_code"]),
        ]

    def __str__(self):
        return f"Country {self.iso_code}: {self.get_name()}"

    def get_name(self, language="ja"):
        """iso codeで指定された言語の国名を取得
        TODO: 言語ごとの国名を取得するように修正"""
        return self.names.get(language, self.names.get("en", ""))

    def get_country_info(self, language="ja"):
        """国の情報を取得
        TODO: 言語ごとの国名・緯度経度を取得するように修正"""
        return {
            "name": self.get_name(language),
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
