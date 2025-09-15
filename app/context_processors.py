import re
from datetime import datetime, timezone
from threading import Thread

from dateutil import parser
from flask import request, session
from flask_babel import format_datetime

from app.models.supabase_client import supabase_service
from app.settings import BASE_DIR, check_locale_paths_and_languages, delete_world_map
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

    cache_key = "AVAILABLE_YEARS"

    cached_data = flask_cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
    )
    available_years = [item["year"] for item in year_data]
    available_years.sort(reverse=True)
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

    cache_key = "TRANSLATED_URLS"

    cached_data = flask_cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    language = "en"

    po_file_path = (
        BASE_DIR / "app" / "translations" / language / "LC_MESSAGES" / "messages.po"
    )
    translated_urls = set()

    try:
        with open(po_file_path, "r", encoding="utf-8") as f:
            po_content = f.read()
    except FileNotFoundError:
        return set()

    exclude_patterns = [
        r"includes/",  # includesディレクトリ
        r"base\.html",  # base.html
        r"404\.html",  # 404.html
    ]

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
                    # 年度ごとに展開
                    year_data = supabase_service.get_data(
                        table="Year",
                        columns=["year"],
                        filters={f"categories__{Operator.IS_NOT}": None},
                        pandas=True,
                    )
                    available_years = year_data["year"].tolist()
                    for year in available_years:
                        # common/foo.html → /{year}/foo
                        url_path = (
                            "/"
                            + str(year)
                            + "/"
                            + template_path.replace("common/", "").replace(".html", "")
                        )
                        translated_urls.add(url_path)
                else:
                    # 2024/foo.html → /2024/foo
                    url_path = "/" + template_path.replace(".html", "")
                    translated_urls.add(url_path)

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
    latest_year = max(get_available_years())
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

    cache_key = "IS_GBB_ENDED_CACHE"

    cached_data = flask_cache.get(cache_key)
    if cached_data is not None:
        return cached_data[year]

    is_gbb_ended_cache = {}

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

    # キャッシュに保存
    is_gbb_ended_cache[year] = latest_year_ends_at < now
    flask_cache.set(cache_key, is_gbb_ended_cache, timeout=None)

    return is_gbb_ended_cache[year]


# MARK: シリアライズ
def _serialize_cache_value(value, max_size=1000):
    """
    キャッシュの値をJSONシリアライズ可能な形式に変換する内部関数。

    Args:
        value: シリアライズする値
        max_size (int): 値の最大サイズ（これを超えると要約表示）

    Returns:
        JSONシリアライズ可能な値
    """
    import json
    from datetime import date, datetime

    try:
        # 基本的なJSON対応型はそのまま返す
        if value is None or isinstance(value, (bool, int, float, str)):
            return value

        # 日付型の場合は文字列に変換
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        # set型の場合はリストに変換
        if isinstance(value, set):
            if len(value) > 20:  # 大きなsetの場合は要約
                return f"Set with {len(value)} items: {list(list(value)[:10])}..."
            return list(value)

        # frozenset型の場合もリストに変換
        if isinstance(value, frozenset):
            if len(value) > 20:  # 大きなfrozensetの場合は要約
                return f"Frozenset with {len(value)} items: {list(list(value)[:10])}..."
            return list(value)

        # tuple型の場合はリストに変換
        if isinstance(value, tuple):
            if len(str(value)) > max_size:
                return f"Tuple with {len(value)} items"
            return list(value)

        # dict型の場合
        if isinstance(value, dict):
            if len(str(value)) > max_size:
                return f"Dict with {len(value)} keys: {list(value.keys())[:10]}..."
            # 再帰的に各値をシリアライズ
            serialized_dict = {}
            for k, v in value.items():
                try:
                    serialized_dict[str(k)] = _serialize_cache_value(v, max_size // 10)
                except Exception:
                    serialized_dict[str(k)] = f"<Unserializable: {type(v).__name__}>"
            return serialized_dict

        # list型の場合
        if isinstance(value, list):
            if len(str(value)) > max_size:
                return f"List with {len(value)} items: {value[:3]}..."
            # 再帰的に各要素をシリアライズ
            return [
                _serialize_cache_value(item, max_size // 10) for item in value[:100]
            ]

        # その他のオブジェクトの場合
        # まずJSONシリアライズを試行
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            # シリアライズできない場合は型情報と文字列表現を返す
            if hasattr(value, "__dict__"):
                return f"<Object: {type(value).__name__}> {str(value)[:100]}..."
            else:
                return f"<{type(value).__name__}> {str(value)[:100]}..."

    except Exception as e:
        return f"<Serialization Error: {str(e)}>"


# MARK: キャッシュ情報
def get_cache_info(flask_cache):
    """
    Flaskキャッシュの情報を取得する関数。

    Args:
        flask_cache: Flaskキャッシュオブジェクト

    Returns:
        dict: キャッシュの情報を含む辞書
            - cache_type (str): キャッシュの種類
            - cache_keys (list): キャッシュに保存されているキーのリスト
            - cache_data (dict): 各キーとその値のペア
            - cache_stats (dict): キャッシュの統計情報
    """
    if flask_cache is None:
        return None

    try:
        cache_info = {}

        # キャッシュの種類によって情報を取得
        cache_backend = flask_cache.cache

        # SimpleCache（メモリキャッシュ）の場合
        if hasattr(cache_backend, "_cache"):
            cache_dict = cache_backend._cache
            all_keys = list(cache_dict.keys())

            # 表示対象のキーを限定
            target_keys = ["AVAILABLE_YEARS", "TRANSLATED_URLS", "IS_GBB_ENDED_CACHE"]
            cache_info["cache_keys"] = [key for key in all_keys if key in target_keys]

            # 指定されたキーの値のみを取得
            for key in cache_info["cache_keys"]:
                try:
                    value = flask_cache.get(key)
                    if value is not None:
                        # JSONシリアライズ可能な形式に変換
                        serialized_value = _serialize_cache_value(value)
                        cache_info[key] = serialized_value
                    else:
                        cache_info[key] = None
                except Exception as e:
                    cache_info[key] = f"Error retrieving value: {str(e)}"

        return cache_info

    except Exception as e:
        return {
            "error": f"Failed to retrieve cache info: {str(e)}",
        }


# MARK: 共通変数
def common_variables(
    BABEL_SUPPORTED_LOCALES,
    LANGUAGES,
    IS_LOCAL,
    IS_PULL_REQUEST,
    LAST_UPDATED,
):
    """
    Flaskのテンプレート共通変数を提供するコンテキストプロセッサ。

    Args:
        BABEL_SUPPORTED_LOCALES (list): サポートされている言語ロケールのリスト。
        LANGUAGES (list): 言語コードと表示名のタプルリスト。
        IS_LOCAL (bool): ローカル環境かどうかのフラグ。
        IS_PULL_REQUEST (bool): プルリクエスト環境かどうかのフラグ。
        LAST_UPDATED (datetime): 最終更新日時

    Returns:
        dict: テンプレートで利用可能な共通変数の辞書。
            - year (int): 現在の年度
            - available_years (list): 利用可能な年度リスト
            - lang_names (list): 言語コードと表示名のタプルリスト
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
    # 年度をURLパスから取得
    year_str = request.path.split("/")[1]
    try:
        year = int(year_str)
    except Exception:
        year = datetime.now().year

    # 言語コード
    language = (
        session["language"]
        if "language" in session and session["language"] in BABEL_SUPPORTED_LOCALES
        else "ja"
    )

    # 翻訳済みURLセット
    translated_urls = get_translated_urls()

    # 各種フラグ
    available_years = get_available_years()
    is_early_access_flag = is_early_access(year)
    is_gbb_ended_flag = is_gbb_ended(year)
    is_latest_year_flag = is_latest_year(year)
    is_translated_flag = is_translated(
        request.path,
        language,
        translated_urls,
    )
    last_updated = format_datetime(LAST_UPDATED, "full")

    # ここに書かないと循環インポートになる
    from app.main import flask_cache

    # キャッシュ情報を取得（開発・PR環境のみ）
    cache_data = get_cache_info(flask_cache) if IS_LOCAL or IS_PULL_REQUEST else None

    return {
        "available_years": available_years,
        "cache_data": cache_data,
        "is_early_access": is_early_access_flag,
        "is_gbb_ended": is_gbb_ended_flag,
        "is_latest_year": is_latest_year_flag,
        "is_local": IS_LOCAL,
        "is_pull_request": IS_PULL_REQUEST,
        "is_translated": is_translated_flag,
        "lang_names": LANGUAGES,
        "language": language,
        "last_updated": last_updated,
        "scroll": request.args.get("scroll", ""),
        "year": year,
    }


# MARK: 言語設定
def get_locale(BABEL_SUPPORTED_LOCALES):
    """
    セッションまたはリクエストから最適な言語ロケールを取得します。

    Args:
        BABEL_SUPPORTED_LOCALES (list): サポートされているロケールのリスト

    Returns:
        str: 選択された言語ロケール（例: "ja", "en" など）

    Note:
        セッションに"language"が設定されていない場合は、リクエストのAccept-Languageヘッダーから
        最適なロケールを選択し、セッションに保存します。該当するロケールがない場合は"ja"をデフォルトとします。
    """
    # クエリパラメータで言語指定されている場合、それを優先
    preferred_language = request.args.get("lang")
    if preferred_language and preferred_language in BABEL_SUPPORTED_LOCALES:
        session["language"] = preferred_language
        return session["language"]

    # セッションに言語が設定されているか確認
    if "language" not in session:
        best_match = request.accept_languages.best_match(BABEL_SUPPORTED_LOCALES)
        session["language"] = best_match if best_match else "ja"
    return session["language"]


# MARK: 初期化タスク
def initialize_background_tasks(BABEL_SUPPORTED_LOCALES):
    """
    バックグラウンドタスクの初期化を行います。

    Args:
        BABEL_SUPPORTED_LOCALES (list): サポートされているロケールのリスト

    Returns:
        None

    Note:
        - delete_world_map、check_locale_paths_and_languages、get_available_years、get_translated_urls
          の各関数をバックグラウンドスレッドで非同期に実行します。
        - check_locale_paths_and_languagesにはBABEL_SUPPORTED_LOCALESが引数として渡されます。
        - 各タスクはアプリケーションの初期化時に一度だけ実行されます。
    """
    Thread(target=delete_world_map).start()
    Thread(
        target=check_locale_paths_and_languages, args=(BABEL_SUPPORTED_LOCALES,)
    ).start()
    Thread(target=get_available_years).start()
    Thread(target=get_translated_urls).start()
