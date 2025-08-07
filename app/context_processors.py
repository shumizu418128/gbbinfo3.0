import re
from datetime import datetime, timezone
from threading import Thread

from dateutil import parser
from flask import g, request, session

from app.models.supabase_client import supabase_service
from app.settings import BASE_DIR, check_locale_paths_and_languages, delete_world_map
from app.util.filter_eq import Operator

AVAILABLE_YEARS = []
TRANSLATED_URLS = set()

is_gbb_ended_cache = {}


def get_available_years():
    """
    年度一覧を取得する関数。

    Returns:
        list: 利用可能な年度（降順）のリスト
    """
    global AVAILABLE_YEARS
    if AVAILABLE_YEARS:
        return AVAILABLE_YEARS

    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
    )
    available_years = [item["year"] for item in year_data]
    available_years.sort(reverse=True)
    AVAILABLE_YEARS = available_years

    return AVAILABLE_YEARS


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

    global TRANSLATED_URLS
    if TRANSLATED_URLS:
        return TRANSLATED_URLS

    language = "en"

    po_file_path = BASE_DIR / "app" / "translations" / language / "LC_MESSAGES" / "messages.po"
    TRANSLATED_URLS = set()

    try:
        with open(po_file_path, "r", encoding="utf-8") as f:
            po_content = f.read()
    except FileNotFoundError:
        return set()

    exclude_patterns = [
        r"\\includes\\",  # includesディレクトリ
        r"base\.html",  # base.html
        r"404\.html",  # 404.html
    ]

    for line in po_content.split("\n"):
        if line.startswith("#: .\\gbbinfojpn\\app\\templates\\"):
            # コメント行から複数パスを取得
            paths = line.replace("#:", "").split()
            for path in paths:
                # 除外条件
                if any(re.search(pattern, path) for pattern in exclude_patterns):
                    continue

                # パスからテンプレート部分を抽出
                m = re.match(r"\.\\gbbinfojpn\\app\\templates\\(.+?\.html)", path)
                if not m:
                    continue
                template_path = m.group(1)

                # 年度ディレクトリ or commonディレクトリ
                if template_path.startswith("common\\"):
                    # 年度ごとに展開
                    year_data = supabase_service.get_data(
                        table="Year",
                        columns=["year"],
                        filters={f"categories__{Operator.IS_NOT}": None},
                        pandas=True,
                    )
                    available_years = year_data["year"].tolist()
                    for year in available_years:
                        # common\foo.html → /{year}/foo
                        url_path = (
                            "/"
                            + str(year)
                            + "/"
                            + template_path.replace("common\\", "").replace(".html", "")
                        )
                        TRANSLATED_URLS.add(url_path)
                else:
                    # 2024\foo.html → /2024/foo
                    url_path = "/" + template_path.replace("\\", "/").replace(
                        ".html", ""
                    )
                    TRANSLATED_URLS.add(url_path)

    return TRANSLATED_URLS


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
    latest_year = max(get_available_years())
    return now <= year <= latest_year


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


def is_translated(url, language, translated_urls):
    """
    指定されたURLが翻訳ファイルに存在するかを判定する。

    Args:
        url (str): 判定するURL
        language (str): 判定する言語

    Returns:
        bool: 翻訳ファイルに存在する場合はTrue、それ以外はFalse
    """
    # 日本語は常にTrue
    if language == "ja":
        return True

    # 定数から翻訳されたURLを取得
    return url in translated_urls


def is_gbb_ended(year):
    """
    指定された年度がGBB終了年度かを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: GBB終了年度の場合はTrue、それ以外はFalse
    """
    global is_gbb_ended_cache
    if year in is_gbb_ended_cache:
        return is_gbb_ended_cache[year]

    # タイムゾーンを考慮した現在時刻を取得
    now = datetime.now(timezone.utc)

    # 過去年度は常にTrue
    if year < now.year:
        return True

    year_data = supabase_service.get_data(
        table="Year",
        columns=["year", "ends_at"],
        filters={f"year__{Operator.EQUAL}": year},
    )
    # 最新年度GBBの終了日を取得
    latest_year_ends_at = year_data[0]["ends_at"]

    # 最新年度終了日がない場合、1つ前のGBB終了日を取得
    if latest_year_ends_at is None:
        latest_year_ends_at = year_data[1]["ends_at"]

    # latest_year_ends_atが文字列の場合はdatetime型に変換
    if isinstance(latest_year_ends_at, str):
        latest_year_ends_at = parser.parse(latest_year_ends_at)

    # latest_year_ends_atがナイーブな場合はタイムゾーンを適用
    if latest_year_ends_at and latest_year_ends_at.tzinfo is None:
        latest_year_ends_at = latest_year_ends_at.replace(tzinfo=timezone.utc)

    is_gbb_ended_cache[year] = latest_year_ends_at < now
    return is_gbb_ended_cache[year]


def common_variables(
    BABEL_SUPPORTED_LOCALES,
    LANGUAGES,
    IS_LOCAL,
    IS_PULL_REQUEST,
    LAST_UPDATED,
):
    """
    全テンプレートで共通して使う変数を返すコンテキストプロセッサ

    Args:
        request (Request): リクエストオブジェクト
        session (SessionMixin): セッションオブジェクト

    Returns:
        dict: テンプレートに渡す共通変数
    """
    # databaseアプリ内では使用しない
    if request.path.startswith("/database/"):
        return {}

    year_str = request.path.split("/")[1]

    # 年度が最新 or 試験公開年度か検証
    try:
        year = int(year_str)
    except Exception:
        year = datetime.now().year

    available_years = get_available_years()
    translated_urls = get_translated_urls()
    is_latest_year_flag = is_latest_year(year)
    is_early_access_flag = is_early_access(year)

    return {
        "year": year,
        "available_years": available_years,
        # 言語のタプルリスト [("ja", "日本語"), ("en", "English"), ...]
        "lang_names": LANGUAGES,
        # 現在の言語コード
        "language": session["language"]
        if "language" in session and session["language"] in BABEL_SUPPORTED_LOCALES
        else "ja",
        "is_translated": is_translated(
            request.path,
            getattr(request, "LANGUAGE_CODE", "ja"),
            translated_urls,
        ),
        "current_url": request.url,
        "last_updated": LAST_UPDATED,
        "is_latest_year": is_latest_year_flag,
        "is_early_access": is_early_access_flag,
        "is_gbb_ended": is_gbb_ended(year),
        "is_local": IS_LOCAL,
        "is_pull_request": IS_PULL_REQUEST,
        "scroll": request.args.get("scroll", ""),
    }


def get_locale(BABEL_SUPPORTED_LOCALES):
    """
    ユーザーの言語設定を取得します。
    利用可能な言語の中から、セッションに保存された言語を優先的に返します。
    セッションに言語が保存されていない場合は、リクエストの受け入れ言語の中から最適な言語を選択します。

    Returns:
        str: ユーザーの言語設定
    """
    # セッションに言語が設定されているか確認
    if "language" not in session:
        best_match = request.accept_languages.best_match(BABEL_SUPPORTED_LOCALES)
        session["language"] = best_match if best_match else "ja"
    return session["language"]


def set_request_data(BABEL_SUPPORTED_LOCALES):
    """
    リクエストごとに実行される関数。
    URLを取得して、グローバル変数に保存します。
    これにより、リクエストのURLをグローバルにアクセスできるようにします。
    また、セッションに言語が設定されていない場合、デフォルトの言語を設定します。

    Returns:
        None
    """
    g.current_url = request.path

    if "X-Forwarded-For" in request.headers:
        user_ip = request.headers["X-Forwarded-For"].split(",")[0].strip()
        print(f"IPアドレス: {user_ip}", flush=True)

    # 初回アクセス時の言語設定
    if "language" not in session:
        best_match = request.accept_languages.best_match(BABEL_SUPPORTED_LOCALES)
        session["language"] = best_match if best_match else "ja"


def initialize_background_tasks(BABEL_SUPPORTED_LOCALES):
    """
    アプリケーション起動時にバックグラウンドで実行する初期化タスクをまとめて起動します。

    Args:
        なし

    Returns:
        None
    """
    Thread(target=delete_world_map).start()
    Thread(
        target=check_locale_paths_and_languages, args=(BABEL_SUPPORTED_LOCALES,)
    ).start()
    Thread(target=get_available_years).start()
    Thread(target=get_translated_urls).start()
