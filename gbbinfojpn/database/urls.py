"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.database.views import views

app_name = "database"

urlpatterns = [
    # Testテーブル関連
    path("test/", views.test, name="test"),  # http://127.0.0.1:8000/database/test/
    path("participants/", views.participants, name="participants"),  # http://127.0.0.1:8000/database/participants/
]
