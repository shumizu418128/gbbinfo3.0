"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.app.views import common, language, participants, result, rule

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
    path(
        "<int:year>/result",
        result.result_view,
        name="result",
    ),
    path(
        "<int:year>/japan",
        participants.participants_country_specific_view,
        name="japan",
    ),
    path(
        "<int:year>/korea",
        participants.participants_country_specific_view,
        name="korea",
    ),
    # その他通常ページ
    path("<int:year>/<str:content>", common.content_view, name="common"),
]
