"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.app.views import (
    beatboxer_tavily_search,
    common,
    gemini_search,
    language,
    participant_detail,
    participants,
    result,
    rule,
    search_participants,
    world_map,
)

app_name = "app"

urlpatterns = [
    # リダイレクト
    path("", common.top_redirect_view, name="redirect_to_latest_top"),
    path("lang", language.change_language, name="change_language"),
    path("2022/<str:content>", common.content_2022_view, name="2022_content"),
    # postリクエスト
    path(
        "beatboxer_tavily_search",
        beatboxer_tavily_search.post_beatboxer_tavily_search,
        name="beatboxer_tavily_search",
    ),
    path(
        "search_suggestions",
        gemini_search.post_gemini_search_suggestion,
        name="search_suggestion",
    ),
    path(
        "<int:year>/search",
        gemini_search.post_gemini_search,
        name="search",
    ),
    path(
        "<int:year>/search_participants",
        search_participants.post_search_participants,
        name="search_participants",
    ),
    # 要データ取得
    path("<int:year>/world_map", world_map.world_map_view, name="world_map"),
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
    path(
        "others/participant_detail",
        participant_detail.participant_detail_view,
        name="participant_detail",
    ),
    # その他通常ページ
    path("others/<str:content>", common.other_content_view, name="others"),
    path("<int:year>/<str:content>", common.content_view, name="common"),
]



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


# 404ハンドラーの設定
handler404 = "gbbinfojpn.app.views.common.not_found_page_view"
