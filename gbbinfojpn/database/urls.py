"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.database.views import views

app_name = "database"

urlpatterns = [
    # Testテーブル関連
    path("test/", views.test, name="test"),
]
