"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.app.views import common, language, participants, rule

app_name = "app"

urlpatterns = [
    # リダイレクト
    path("", common.top_redirect_view, name="redirect_to_latest_top"),
    path("lang", language.change_language, name="change_language"),
    # 要データ取得
    path("<int:year>/rule", rule.rules_view, name="rule"),
    path(
        "<int:year>/participants", participants.participants_view, name="participants"
    ),
    # その他通常ページ
    path("<int:year>/<str:content>", common.content_view, name="common"),
]
