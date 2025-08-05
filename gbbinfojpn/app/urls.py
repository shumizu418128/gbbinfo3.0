"""
databaseアプリのURL設定
"""

from django.urls import path

from gbbinfojpn.app.views import (
    beatboxer_tavily_search,
    gemini_search,
    common,
    language,
    participant_detail,
    participants,
    result,
    rule,
    world_map,
)

app_name = "app"

urlpatterns = [
    # リダイレクト
    path("", common.top_redirect_view, name="redirect_to_latest_top"),
    path("lang", language.change_language, name="change_language"),
    # postリクエスト
    path(
        "beatboxer_tavily_search",
        beatboxer_tavily_search.post_beatboxer_tavily_search,
        name="beatboxer_tavily_search",
    ),
    path(
        "<int:year>/search",
        gemini_search.post_gemini_search,
        name="search",
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
