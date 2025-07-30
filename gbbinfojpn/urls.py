from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    # システム監視
    path("health/", lambda _: HttpResponse("OK"), name="health_check"),
    path("", include("gbbinfojpn.app.urls", namespace="app")),
]

if settings.DEBUG:
    urlpatterns.append(
        path(
            "database/",
            include(
                "gbbinfojpn.database.urls",
                namespace="database",
            ),
        ),
    )

# 404ハンドラーの設定
handler404 = "gbbinfojpn.app.views.common.not_found_page_view"
