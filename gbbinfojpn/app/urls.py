"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.app.views import common, language, rule

app_name = "app"

urlpatterns = [
    path("", common.top_redirect_view, name="redirect_to_latest_top"),
    path("lang", language.change_language, name="change_language"),
    path("<int:year>/rule", rule.rules_view, name="rule"),
    path("<int:year>/<str:content>", common.content_view, name="common"),
]
