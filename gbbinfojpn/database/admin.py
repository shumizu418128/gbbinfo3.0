from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite

from .models import DatabaseEntry


class DatabaseAdminSite(AdminSite):
    site_header = "Database管理画面"
    site_title = "Database Admin"
    index_title = "Database管理"


# カスタムAdminサイトのインスタンスを作成
database_admin_site = DatabaseAdminSite(name="database_admin")


class DatabaseEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "description")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")


# ローカル環境でのみ利用可能
if settings.DEBUG:
    database_admin_site.register(DatabaseEntry, DatabaseEntryAdmin)
