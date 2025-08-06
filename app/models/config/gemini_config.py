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

PROMPT = """# あなたの仕事
以下の文は、Grand Beatbox Battle {year} (略称: GBB{year})に興味があるユーザーから来た質問です。
「{question}」

質問に対してもっとも適切なWebページURLとクエリパラメータを選択してください。
webサイトのURLは以下の通りです。ディレクトリは必ず{year}になります。
https://gbbinfo-jpn.onrender.com/{year}/

# 回答のルール
このURLの後ろに、以下のファイル名を必ず含めてください。
また、提示されたリストの中から、質問内容に最も合致するクエリパラメータを1つ選択してください。
そして、質問文から、GBBに関連すると思われる人名やグループ名を最初に見つかったもの1つだけ抽出し、アルファベット表記（例: ROFU, Wing）に変換して name フィールドに設定してください。見つからない場合は None としてください。
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
もしも質問文全体が、特定の人名やグループ名（例: Tomazacre、River'）のみで構成されている、あるいは明らかに特定人物に関する検索意図だと判断できる場合、ファイル名はparticipantsを、クエリパラメータはsearch_participantsを選択してください。
なお、GBBの部門には、Solo, Tag Team, Loopstation, Producer, Crewなどがあります。

# 回答例1
{{"url": "https://gbbinfo-jpn.onrender.com/{year}/top", "parameter": "contact", "name": "None"}}

# 回答例2
{{"url": "https://gbbinfo-jpn.onrender.com/{year}/participants", "parameter": "search_participants", "name": "ROFU"}}"""
