from datetime import datetime, timedelta, timezone
from pathlib import Path

LANGUAGE_CHOICES = [
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("en", "English"),
    ("be", "Беларуская"),
    ("cs", "Čeština"),
    ("da", "Dansk"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("et", "Eesti"),
    ("fr", "Français"),
    ("hi", "हिन्दी"),
    ("hu", "Magyar"),
    ("it", "Italiano"),
    ("ms", "Bahasa MY"),
    ("no", "Norsk"),
    ("pl", "Polski"),
    ("pt", "Português"),
    ("ta", "தமிழ்"),
    ("zh_Hans_CN", "简体中文"),
    ("zh_Hant_TW", "繁體中文"),
]

LANGUAGE_NAMES = {code: name for code, name in LANGUAGE_CHOICES}

SUPPORTED_LOCALES = [code for code, _ in LANGUAGE_CHOICES]

SEARCH_CACHE = {
    "7TO": "/__year__/top_7tosmoke",
    "7TOSMOKE": "/__year__/top_7tosmoke",
    "日程": "/__year__/top?scroll=date",
    "スケジュール": "/__year__/timetable",
    "タイムテーブル": "/__year__/timetable",
    "時間": "/__year__/timetable",
    "일정": "/__year__/timetable",
    "チケット": "/__year__/ticket",
    "会場": "/__year__/ticket",
    "場所": "/__year__/ticket",
    "開催地": "/__year__/ticket",
    "審査員": "/__year__/rule?scroll=judges",
    "CREW": "/__year__/rule?scroll=category",
    "LOOP": "/__year__/rule?scroll=category",
    "LOOPSTATION": "/__year__/rule?scroll=category",
    "SHOWCASE": "/__year__/rule?scroll=category",
    "SOLO": "/__year__/rule?scroll=category",
    "ソロ": "/__year__/rule?scroll=category",
    "TAG": "/__year__/rule?scroll=category",
    "タッグ": "/__year__/rule?scroll=category",
    "ルール": "/__year__/rule",
    "トーナメント": "/__year__/result",
    "優勝": "/__year__/result",
    "優勝者": "/__year__/result",
    "ROFU": "/__year__/participants?scroll=search_participants",
    "ロフ": "/__year__/participants?scroll=search_participants",
    "HIKAKIN": "/__year__/participants?scroll=search_participants",
    "ヒカキン": "/__year__/participants?scroll=search_participants",
    "윙": "/__year__/participants?scroll=search_participants",
    "WING": "/__year__/participants?scroll=search_participants",
    "今年の出場者": "/__year__/participants",
    "出場者": "/__year__/participants",
    "誰が出る": "/__year__/participants",
    "辞退": "/__year__/participants",
    "辞退者": "/__year__/participants",
    "通過者": "/__year__/participants",
    "WILDCARD結果": "/__year__/participants",
    "ワイルドカード結果": "/__year__/participants",
    "참가자": "/__year__/participants",
    "日本人": "/__year__/japan",
    "ワイルドカード一覧": "/__year__/wildcards",
    "WILDCARD一覧": "/__year__/wildcards",
    "現地観戦計画のたてかた": "/travel/top",
}

FOLIUM_CUSTOM_CSS = """
<style>
    /* より強い詳細度でBootstrapのスタイルを上書き */
    .leaflet-popup-content a,
    .leaflet-popup-content-wrapper a,
    div a {
        color: rgb(0, 68, 204) !important;
        word-wrap: break-word;
        text-decoration: underline;
    }

    .leaflet-popup-content a:hover,
    .leaflet-popup-content-wrapper a:hover,
    div a:hover {
        color: rgb(255, 100, 23) !important;
        text-decoration: underline;
    }

    .leaflet-popup-content a:active,
    .leaflet-popup-content-wrapper a:active,
    div a:active {
        color: rgb(0, 68, 204) !important;
    }
</style>
"""
NASA_GIBS_ATTR = '<a href="https://earthdata.nasa.gov">NASA GIBS (Global Imagery Browse Services)</a>'
NASA_GIBS_TILES = (
    "https://gibs-{s}.earthdata.nasa.gov/wmts/epsg3857/best/"
    "VIIRS_CityLights_2012/default//GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg"
)

MULTI_COUNTRY_TEAM_ISO_CODE = 9999
ISO_CODE_NOT_FOUND = "beatboxer_dataにiso_codeが存在しません Participantテーブルを取得する際に、iso_codeを取得してください"
COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND = "ParticipantMemberにCountry(names, iso_alpha2)が存在しません Participantテーブルを取得する際に、Country(names, iso_alpha2)をjoinさせてください"
COUNTRY_ISO_ALPHA2_NOT_FOUND = "ParticipantMemberにCountry(iso_alpha2)が存在しません Participantテーブルを取得する際に、Country(iso_alpha2)をjoinさせてください"

YOUTUBE_CHANNEL_PATTERN = (
    r"^(https?:\/\/)?(www\.)?youtube\.com\/(c\/|channel\/|user\/|@)[a-zA-Z0-9_-]+\/?$"
)
INSTAGRAM_ACCOUNT_PATTERN = r"^(https?:\/\/)?(www\.)?instagram\.com\/[a-zA-Z0-9_.]+\/?$"
FACEBOOK_ACCOUNT_PATTERN = (
    r"^(https?:\/\/)?((www|m)\.)?facebook\.com\/[a-zA-Z0-9_.]+\/?$"
)
SPOTIFY_ACCOUNT_PATTERN = (
    r"^(https?:\/\/)?(open\.)?spotify\.com\/artist\/[a-zA-Z0-9]+\/?$"
)
TWITTER_ACCOUNT_PATTERN = (
    r"^(https?:\/\/)?(www\.)?(twitter\.com|x\.com)\/[a-zA-Z0-9_]+\/?$"
)
SOUNDCLOUD_ACCOUNT_PATTERN = (
    r"^(https?:\/\/)?(www\.)?soundcloud\.com\/[a-zA-Z0-9_-]+\/?$"
)

BAN_WORDS = ["HATEN", "BEATCITY", "BCJ", "JPN CUP", "WIKI", "/PLAYLIST"]

FLAG_CODE = """
<picture>
    <source
        type="image/webp"
        srcset="https://flagcdn.com/28x21/{iso_alpha2}.webp,
        https://flagcdn.com/56x42/{iso_alpha2}.webp 2x,
        https://flagcdn.com/84x63/{iso_alpha2}.webp 3x">
    <source
        type="image/png"
        srcset="https://flagcdn.com/28x21/{iso_alpha2}.png,
        https://flagcdn.com/56x42/{iso_alpha2}.png 2x,
        https://flagcdn.com/84x63/{iso_alpha2}.png 3x">
    <img
        src="https://flagcdn.com/28x21/{iso_alpha2}.png"
        width="28"
        height="21">
</picture>
"""

BASE_DIR = Path(__file__).resolve().parent.parent.parent

MINUTE = 60
HOUR = 60 * MINUTE

LAST_UPDATED = datetime.now(timezone(timedelta(hours=9)))

ALL_DATA = "*"
