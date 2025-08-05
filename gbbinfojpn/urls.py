from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from gbbinfojpn.app.sitemaps import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    # システム監視
    path("health/", lambda _: HttpResponse("OK"), name="health_check"),
    # サイトマップ
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
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
