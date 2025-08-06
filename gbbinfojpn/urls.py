from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from gbbinfojpn.app.sitemaps import StaticViewSitemap
from gbbinfojpn.app.views.static_files import (
    ads_txt,
    apple_touch_icon,
    discord,
    favicon_ico,
    manifest_json,
    robots_txt,
    service_worker_js,
)

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    # システム監視
    path("health", lambda _: HttpResponse("OK"), name="health_check"),
    # 静的ファイル
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("ads.txt", ads_txt, name="ads_txt"),
    path("manifest.json", manifest_json, name="manifest_json"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("favicon.ico", favicon_ico, name="favicon_ico"),
    path("service-worker.js", service_worker_js, name="service_worker_js"),
    path(
        "apple-touch-icon-152x152-precomposed.png",
        apple_touch_icon,
        name="apple_touch_icon_152_precomposed",
    ),
    path("apple-touch-icon-152x152.png", apple_touch_icon, name="apple_touch_icon_152"),
    path(
        "apple-touch-icon-120x120-precomposed.png",
        apple_touch_icon,
        name="apple_touch_icon_120_precomposed",
    ),
    path("apple-touch-icon-120x120.png", apple_touch_icon, name="apple_touch_icon_120"),
    path(
        "apple-touch-icon-precomposed.png",
        apple_touch_icon,
        name="apple_touch_icon_precomposed",
    ),
    path("apple-touch-icon.png", apple_touch_icon, name="apple_touch_icon"),
    path(".well-known/discord", discord, name="discord"),
    # アプリケーションのURL
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
