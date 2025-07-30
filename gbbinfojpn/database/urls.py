"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.database.views import test, participant, result

app_name = "database"

urlpatterns = [
    # Testテーブル関連
    path("test", test.test_view, name="test"),  # http://127.0.0.1:8000/database/test
    path(
        "participants", participant.participants_view, name="participants"
    ),  # http://127.0.0.1:8000/database/participants
    path(
        "results", result.results_view, name="results"
    ),  # http://127.0.0.1:8000/database/results
]
