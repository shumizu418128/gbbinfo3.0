from google.genai import types

SAFETY_SETTINGS_BLOCK_ONLY_HIGH = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
]

SAFETY_SETTINGS_BLOCK_NONE = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

SEARCH_CACHE = {
    "7TO": "/__year__/top_7tosmoke",
    "7TOSMOKE": "/__year__/top_7tosmoke",
    "日程": "/__year__/top?scroll=date",
    "SHOWCASE": "/__year__/time_schedule?scroll=showcase",
    "スケジュール": "/__year__/time_schedule",
    "タイムスケジュール": "/__year__/time_schedule",
    "タイムテーブル": "/__year__/time_schedule",
    "時間": "/__year__/time_schedule",
    "일정": "/__year__/time_schedule",
    "チケット": "/__year__/ticket",
    "会場": "/__year__/ticket",
    "場所": "/__year__/ticket",
    "開催地": "/__year__/ticket",
    "審査員": "/__year__/rule?scroll=judges",
    "CREW": "/__year__/rule?scroll=category",
    "LOOP": "/__year__/rule?scroll=category",
    "LOOPSTATION": "/__year__/rule?scroll=category",
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
    "現地観戦計画のたてかた": "/others/how_to_plan",
}

PROMPT = """# あなたの仕事
以下の文は、Grand Beatbox Battle {year} (略称: GBB{year})に興味があるユーザーから来た質問です。
「{question}」

質問に対してもっとも適切なWebページURLとクエリパラメータを選択してください。
webサイトのURLは以下の通りです。ディレクトリは必ず{year}になります。
https://gbbinfo-jpn.onrender.com/{year}/

# 回答のルール
このURLの後ろに、以下のファイル名を必ず含めてください。
また、提示されたリストの中から、質問内容に最も合致するクエリパラメータを1つ選択してください。
以下に書かれていないものを作り出す行為は禁止。

- japan: GBB{year}の日本代表出場者
    クエリパラメータ
    - None
- participants: GBB{year}の出場者・辞退者・Wildcardの結果順位・出場者世界地図・出場者名検索
    クエリパラメータ
    - None
    - search_participants
- result: GBB{year}の大会結果
    クエリパラメータ
    - None
- rule: GBB{year}の開催部門一覧、シード権獲得条件、ルール、Wildcardの結果発表日程、審査員一覧
    クエリパラメータ
    - None
    - category
    - seeds
    - result_date
    - judges
- stream: GBB{year}の当日配信URL
    クエリパラメータ
    - None
- ticket: GBB{year}のチケット、会場、7toSmokeのチケット、会場
    クエリパラメータ
    - None
- time_schedule: GBB{year}のタイムスケジュール、7toSmokeのタイムスケジュール、スペシャルSHOWCASEについて
    クエリパラメータ
    - None
    - 7tosmoke
    - showcase
- top: GBB{year}開催日
    クエリパラメータ
    - None
    - date
    - contact
- wildcards: GBB{year}のWildcard動画一覧
    クエリパラメータ
    - None
- result_stream: GBB{year}のWildcardの結果発表配信について
    クエリパラメータ
    - None
- how_to_plan: 現地観戦計画のたてかた、GBBを現地観戦するうえで気を付けるべきこと、交通手段、ホテル、当日の行動、持ち物
    クエリパラメータ
    - None
    - transportation
    - hotel
    - activities
    - items
- about: このwebサイトについて
    クエリパラメータ
    - None
- 7tosmoke: 7tosmokeとは何か、事前予選・当日予選ルール、本戦ルール、7tosmoke最新情報
    クエリパラメータ
    - None
    - qualifying_rules
    - main_event_rules
    - latest_info

もしも適切なWebページが無いと判断した場合、ファイル名はtopを、クエリパラメータはNoneを選択してください。
なお、GBBの部門には、Solo, Tag Team, Loopstation, Producer, Crewなどがあります。

# 回答例1
{{"url": "https://gbbinfo-jpn.onrender.com/{year}/top", "parameter": "None"}}

# 回答例2
{{"url": "https://gbbinfo-jpn.onrender.com/{year}/participants", "parameter": "search_participants"}}"""

PROMPT_TRANSLATE = """Translate this text to {lang}.
Keep names in English. Return JSON only. Strictly follow the JSON format for output:
{{
    "translated_text": "translation here"
}}

Text: {text}
"""

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

MULTI_COUNTRY_TEAM_ISO_CODE = 9999

ISO_CODE_NOT_FOUND = "beatboxer_dataにiso_codeが存在しません Participantテーブルを取得する際に、iso_codeを取得してください"
ISO_CODE_COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND = "ParticipantMemberにCountry(names, iso_alpha2)が存在しません Participantテーブルを取得する際に、Country(names, iso_alpha2)をjoinさせてください"
ISO_CODE_COUNTRY_ISO_ALPHA2_NOT_FOUND = "ParticipantMemberにCountry(iso_alpha2)が存在しません Participantテーブルを取得する際に、Country(iso_alpha2)をjoinさせてください"

YOUTUBE_CHANNEL_PATTERN = (
    r"^(https?:\/\/)?(www\.)?youtube\.com\/(c\/|channel\/|user\/|@)[a-zA-Z0-9_-]+\/?$"
)
INSTAGRAM_ACCOUNT_PATTERN = r"^(https?:\/\/)?(www\.)?instagram\.com\/[a-zA-Z0-9_.]+\/?$"
FACEBOOK_ACCOUNT_PATTERN = r"^(https?:\/\/)?(www\.)?facebook\.com\/[a-zA-Z0-9_.]+\/?$"

BAN_WORDS = ["HATEN", "BEATCITY", "JPN CUP", "WIKI", "/PLAYLIST"]

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
