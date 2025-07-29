"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.app.views import common, language

app_name = "app"

urlpatterns = [
    path("", common.redirect_to_latest_top, name="redirect_to_latest_top"),
    path("lang", language.change_language, name="change_language"),
    path("<int:year>/<str:content>", common.common, name="common"),
]
