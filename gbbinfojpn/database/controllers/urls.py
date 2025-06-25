"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.database.views import views

app_name = "database"

urlpatterns = [
    # ウェブコンテンツ関連
    path("content/", views.web_content_list, name="content_list"),
    path("content/<int:content_id>/", views.content_detail, name="content_detail"),
    # Testテーブル関連
    path("test/", views.test_data_list, name="test_data_list"),
    # API エンドポイント
    path("api/content/", views.api_content, name="api_content"),
    path("api/entries/", views.api_database_entries, name="api_entries"),
    # システム監視
    path("health/", views.health_check, name="health_check"),
]
