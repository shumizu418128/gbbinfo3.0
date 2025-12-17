import re
from datetime import datetime, timezone
from threading import Thread
from urllib.parse import urlparse, urlunparse

from dateutil import parser
from flask import redirect, request, session
from flask_babel import format_datetime

from app.config.config import (
    BASE_DIR,
    LANGUAGE_CHOICES,
    LAST_UPDATED,
    SUPPORTED_LOCALES,
)
from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator


# MARK: 年度一覧
def get_available_years():
    """
    年度一覧を取得する関数。

    Returns:
        list: 利用可能な年度（降順）のリスト
    """
    # ここに書かないと循環インポートになる
    from app.main import flask_cache

    cache_key = "available_years"
    cached_years = flask_cache.get(cache_key)

    if cached_years is not None:
        return cached_years

    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
    )
    available_years = [item["year"] for item in year_data]
    available_years.sort(reverse=True)

    # キャッシュに保存（タイムアウトなし）
    flask_cache.set(cache_key, available_years, timeout=None)

    return available_years


# MARK: 翻訳済URL
def get_translated_urls():
    r"""
    英語（en）のmessages.poファイルから、翻訳済みページのURLパス一覧を取得する内部関数。

    Returns:
        set: 翻訳が存在するページのURLパスのセット

    Note:
        messages.poのmsgidコメント（例: #: .\gbbinfojpn\app\templates\2024\rule.html:3）から
        テンプレートパスを抽出し、URLパスに変換します。
        common/配下のテンプレートは年度ごとに展開されるため、全年度分を生成します。
        base.html, includes, 404.html等は除外します。
    """
    # ここに書かないと循環インポートになる
    from app.main import flask_cache

    cache_key = "translated_urls"
    cached_urls = flask_cache.get(cache_key)

    if cached_urls is not None:
        return cached_urls

    po_file_path = (
        BASE_DIR / "app" / "translations" / "en" / "LC_MESSAGES" / "messages.po"
    )
    translated_urls = set()

    try:
        with open(po_file_path, "r", encoding="utf-8") as f:
            po_content = f.read()
    except FileNotFoundError:
        return set()

    exclude_patterns = [
        r"includes/",
        r"base\.html",
        r"404\.html",
    ]

    # 年度ごとに展開（中止年度は除外）
    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
        filters={f"categories__{Operator.IS_NOT}": None},
        pandas=True,
    )
    available_years = year_data["year"].tolist()

    for lang in SUPPORTED_LOCALES:
        for line in po_content.split("\n"):
            if line.startswith("#: templates/"):
                # コメント行から複数パスを取得
                paths = line.replace("#:", "").split()
                for path in paths:
                    # 除外条件
                    if any(re.search(pattern, path) for pattern in exclude_patterns):
                        continue

                    # パスからテンプレート部分を抽出
                    m = re.match(r"templates/(.+?\.html)", path)
                    if not m:
                        continue
                    template_path = m.group(1)

                    # 年度ディレクトリ or commonディレクトリ
                    if template_path.startswith("common/"):
                        for year in available_years:
                            # common/foo.html -> /{lang}/{year}/foo
                            url_path = (
                                "/"
                                + lang
                                + "/"
                                + str(year)
                                + "/"
                                + template_path.replace("common/", "").replace(
                                    ".html", ""
                                )
                            )
                            translated_urls.add(url_path)
                    else:
                        # 2024/foo.html -> /{lang}/2024/foo
                        url_path = "/" + lang + "/" + template_path.replace(".html", "")
                        translated_urls.add(url_path)

    # キャッシュに保存（タイムアウトなし）
    flask_cache.set(cache_key, translated_urls, timeout=None)

    return translated_urls


# MARK: 最新年度
def is_latest_year(year):
    """
    指定された年度が最新年度または今年であるかを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: 最新年度または今年の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    available_years = get_available_years()

    # 利用可能な年度がない場合は現在年度と比較
    if not available_years:
        return year == now

    latest_year = max(available_years)
    return now <= year <= latest_year


# MARK: 試験公開年度
def is_early_access(year):
    """
    指定された年度が、試験公開年度かを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: 試験公開年度の場合はTrue、それ以外はFalse
    """
    dt_now = datetime.now()
    now = dt_now.year
    return year > now


# MARK: 翻訳対応可否
def is_translated(url, language, translated_urls):
    """
    指定されたURLが指定言語で翻訳されているかどうかを判定します。

    Args:
        url (str): 判定するURL
        language (str): 言語コード（例: 'en', 'ja' など）
        translated_urls (set): 翻訳済みURLのセット

    Returns:
        bool: 翻訳されている場合はTrue、そうでない場合はFalse
    """
    # 日本語は常にTrue
    if language == "ja":
        return True

    # 定数から翻訳されたURLを取得
    return url in translated_urls


# MARK: GBB終了年度
def is_gbb_ended(year):
    """
    指定された年度がGBB終了年度かを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: GBB終了年度の場合はTrue、それ以外はFalse
    """
    # ここに書かないと循環インポートになる
    from app.main import flask_cache

    cache_key = f"gbb_ended_{year}"
    cached_result = flask_cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    # タイムゾーンを考慮した現在時刻を取得
    now = datetime.now(timezone.utc)

    # 過去年度は常にTrue
    if year < now.year:
        flask_cache.set(cache_key, True)
        return True

    # 年度データを取得
    year_data = supabase_service.get_data(
        table="Year",
        columns=["year", "ends_at"],
        filters={"year": year},
    )

    # データが存在しない場合 (おそらくありえない)
    if not year_data:
        flask_cache.set(cache_key, False)
        return False

    # 終了日時が設定されていない場合 (未定 = まだ始まっていない とみなす)
    ends_at = year_data[0]["ends_at"]
    if not ends_at:
        flask_cache.set(cache_key, False)
        return False

    # 終了日時と現在時刻を比較
    datetime_ends_at = parser.parse(ends_at)
    result = datetime_ends_at < now
    flask_cache.set(cache_key, result)
    return result


# MARK: 言語URL
def get_change_language_url(current_url):
    """
    現在のURLに対して、各言語ごとにlangクエリパラメータを付与したURLリストを生成します。

    Args:
        current_url (str): 現在のURL。

    Returns:
        list: 各言語ごとの(url, lang_name)のタプルリスト。
    """
    change_language_urls = []
    parsed_url = urlparse(current_url)
    current_language = session.get("language", "")

    for lang_code, lang_name in LANGUAGE_CHOICES:
        # path の言語部分を置換して新しいパスを作る
        new_path = (
            parsed_url.path.replace(f"/{current_language}/", f"/{lang_code}/")
            if current_language
            else parsed_url.path
        )
        new_url = urlunparse(
            ("", "", new_path, parsed_url.params, parsed_url.query, parsed_url.fragment)
        )
        change_language_urls.append((new_url, lang_name))

    return change_language_urls


# MARK: 共通変数
def common_variables(
    IS_LOCAL,
    IS_PULL_REQUEST,
):
    """
    Flaskのテンプレート共通変数を提供するコンテキストプロセッサ。

    Args:
        IS_LOCAL (bool): ローカル環境かどうかのフラグ。
        IS_PULL_REQUEST (bool): プルリクエスト環境かどうかのフラグ。

    Returns:
        dict: テンプレートで利用可能な共通変数の辞書。
            - year (int): 現在の年度
            - available_years (list): 利用可能な年度リスト
            - change_language_urls (list): 言語ごとのURLと表示名のタプルリスト
            - language (str): 現在の言語コード
            - is_translated (bool): 現在のページが翻訳済みかどうか
            - last_updated (str): 最終更新日時
            - is_latest_year (bool): 最新年度かどうか
            - is_early_access (bool): 試験公開年度かどうか
            - is_gbb_ended (bool): GBBが終了しているかどうか
            - is_local (bool): ローカル環境かどうか
            - is_pull_request (bool): プルリクエスト環境かどうか
            - scroll (str): スクロール位置（クエリパラメータ）
    """
    year_str = request.path.split("/")[1]

    # 年度が最新 or 試験公開年度か検証
    try:
        year = int(year_str)
    except Exception:
        year = datetime.now().year

    translated_urls = get_translated_urls()
    language = session["language"]

    return {
        "year": year,
        "available_years": get_available_years(),
        "change_language_urls": get_change_language_url(request.url),
        "language": language,
        "is_translated": is_translated(request.path, language, translated_urls),
        "last_updated": format_datetime(LAST_UPDATED, "full"),
        "is_latest_year": is_latest_year(year),
        "is_early_access": is_early_access(year),
        "is_gbb_ended": is_gbb_ended(year),
        "is_local": IS_LOCAL,
        "is_pull_request": IS_PULL_REQUEST,
        "scroll": request.args.get("scroll", ""),
    }


# MARK: 言語設定
def get_locale():
    """
    セッションまたはリクエストから最適な言語ロケールを取得します。

    Returns:
        str: 選択された言語ロケール（例: "ja", "en" など）

    Note:
        セッションに"language"が設定されていない場合は、リクエストのAccept-Languageヘッダーから
        最適なロケールを選択し、セッションに保存します。該当するロケールがない場合は"ja"をデフォルトとします。
    """
    # URL の最初のパス要素を優先
    preferred_language = (
        request.path.split("/")[1] if request.path.startswith("/") else None
    )

    # セッションが無い、もしくは空文字の場合、Accept-Language から判定
    if "language" not in session or session.get("language", "") == "":
        best_match = request.accept_languages.best_match(SUPPORTED_LOCALES)
        session["language"] = best_match if best_match else "ja"
    # URL の言語がサポート済みなら優先
    elif preferred_language in SUPPORTED_LOCALES:
        session["language"] = preferred_language

    return session["language"]


def redirect_based_on_language():
    """
    URL に言語コードが含まれていない場合、セッションの言語コードを付与してリダイレクトする。
    """
    # participant_detail は特例で /participant_detail/... のまま扱う
    if request.path.startswith("/participant_detail"):
        return add_language_and_redirect()

    # パスに'/'が2つしか含まれていない（例: /2024/foo）場合は言語追加
    if request.path.count("/") == 2:
        # 検索APIなどは除外
        if request.path.endswith("/search") or request.path.endswith(
            "/search_participants"
        ):
            return
        return add_language_and_redirect()


def add_language_and_redirect():
    """
    現在の URL の先頭に session['language'] を付与してリダイレクトする。
    """
    parsed_url = urlparse(request.url)
    new_path = "/" + session.get("language", "ja") + parsed_url.path
    new_url = urlunparse(
        ("", "", new_path, parsed_url.params, parsed_url.query, parsed_url.fragment)
    )
    return redirect(new_url)


# MARK: 世界地図初期化
def delete_world_map():
    """
    world_mapディレクトリ内の全てのHTMLファイルを削除します。

    app/templates配下の各年度ディレクトリ内に存在するworld_mapディレクトリを探索し、
    その中に含まれる全ての.htmlファイルを削除します。
    ディレクトリやファイルが存在しない場合は何も行いません。

    Raises:
        OSError: ファイルの削除に失敗した場合
    """
    templates_dir = BASE_DIR / "app" / "templates"
    if templates_dir.is_dir():
        for html_file in templates_dir.glob("*/world_map/*.html"):
            html_file.unlink()


# MARK: others
def get_others_content():
    """
    'Others'カテゴリに属するコンテンツを取得します。

    Returns:
        list: 'Others'カテゴリに属するコンテンツのリスト
    """
    file_names = []
    for html_file in BASE_DIR.glob("app/templates/others/*.html"):
        file_names.append(html_file.stem)
    return file_names


# MARK: travel
def get_travel_content():
    """
    'Travel'カテゴリに属するコンテンツを取得します。

    Returns:
        list: 'Travel'カテゴリに属するコンテンツのリスト
    """
    file_names = []
    for html_file in BASE_DIR.glob("app/templates/travel/*.html"):
        file_names.append(html_file.stem)
    return file_names


# MARK: 年度別
def get_yearly_content(AVAILABLE_YEARS):
    """
    指定された年度のコンテンツを取得します。

    Args:
        AVAILABLE_YEARS (list): 対象の年度リスト

    Returns:
        list: 指定された年度のコンテンツのリスト
    """
    years_list = []
    contents_per_year = []
    for year in AVAILABLE_YEARS:
        for html_file in BASE_DIR.glob(f"app/templates/{year}/*.html"):
            contents_per_year.append(html_file.stem)
            years_list.append(year)

    return years_list, contents_per_year


# MARK: 出場者id
def get_participant_id():
    """
    参加者のIDリストと各参加者のモードリストを返します。

    Returns:
    tuple: (participants_id_list, participants_mode_list)
        - participants_id_list: list[int | str] — 参加者またはメンバーのIDのリスト（順序は取得順）
        - participants_mode_list: list[str] — 各IDに対応するモードのリスト。値は "team", "single", "team_member" のいずれか。
    """

    # ここに書かないと循環インポートになる
    from app.main import flask_cache

    cache_key = "participant_id_mode_list"
    cached_data = flask_cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    participants_id_list = []
    participants_mode_list = []

    # 出場者データを取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name"],
        join_tables={
            "Category": ["is_team"],
        },
        filters={f"iso_code__{Operator.GREATER_THAN}": 0},
    )
    participant_members_data = supabase_service.get_data(
        table="ParticipantMember",
        columns=["id"],
    )

    for participant in participants_data:
        if participant["Category"]["is_team"]:
            mode = "team"
        else:
            mode = "single"
        participants_id_list.append(participant["id"])
        participants_mode_list.append(mode)

    for member in participant_members_data:
        participants_id_list.append(member["id"])
        participants_mode_list.append("team_member")

    flask_cache.set(
        cache_key, (participants_id_list, participants_mode_list), timeout=None
    )

    return participants_id_list, participants_mode_list


# MARK: 初期化タスク
def initialize_background_tasks(IS_LOCAL):
    """
    バックグラウンドタスクを初期化して同期的に必要なコンテンツを取得します。

    この関数は以下を行います：
    - IS_LOCAL が True の場合、delete_world_map を別スレッドで起動（非同期、fire-and-forget）。
    - get_translated_urls を別スレッドで起動（非同期、fire-and-forget）。
    - get_available_years、get_others_content、get_yearly_content を同期的に呼び出し、その結果を返す。

    引数:
        IS_LOCAL (bool): ローカル環境フラグ。True のとき delete_world_map を並列実行する。

    戻り値:
        tuple:
            - AVAILABLE_YEARS: get_available_years() の戻り値（利用可能な年一覧など）。
            - OTHERS_CONTENT: get_others_content() の戻り値（その他共通コンテンツ）。
            - YEARLY_CONTENT: get_yearly_content(AVAILABLE_YEARS) の戻り値（年度別コンテンツ）。

    注意:
        - 別スレッドで起動されるタスク（delete_world_map, get_translated_urls）は
          fire-and-forget であり、この関数はそれらの完了を待ちません。
        - 非同期タスク内で発生した例外はここでは捕捉されません。必要ならタスク内で例外処理を行ってください。
        - 本関数はアプリケーション初期化時に一度だけ呼び出すことを想定しています。
    """
    if IS_LOCAL:
        Thread(target=delete_world_map).start()
    Thread(target=get_translated_urls).start()
