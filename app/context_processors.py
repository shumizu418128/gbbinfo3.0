from datetime import datetime, timezone

from dateutil import parser
from flask import request, session
from util.filter_eq import Operator

from app import settings
from app.models.supabase_client import supabase_service


def get_available_years():
    """
    年度一覧を取得する関数。

    Returns:
        list: 利用可能な年度（降順）のリスト
    """
    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
    )
    available_years = [item["year"] for item in year_data]
    available_years.sort(reverse=True)

    return available_years


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


def is_translated(url, language):
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
    return url in settings.TRANSLATED_URLS


def is_gbb_ended(year):
    """
    指定された年度がGBB終了年度かを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: GBB終了年度の場合はTrue、それ以外はFalse
    """
    # タイムゾーンを考慮した現在時刻を取得
    now = timezone.now()

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
    if latest_year_ends_at and timezone.is_naive(latest_year_ends_at):
        latest_year_ends_at = timezone.make_aware(latest_year_ends_at)

    return latest_year_ends_at < now


def common_variables():
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
    available_years = get_available_years()

    # 年度が最新 or 試験公開年度か検証
    try:
        year = int(year_str)
    except Exception:
        year = datetime.now().year

    is_latest_year_flag = is_latest_year(year)
    is_early_access_flag = is_early_access(year)

    return {
        "year": year,
        "available_years": available_years,
        # 言語のタプルリスト [("ja", "日本語"), ("en", "English"), ...]
        "lang_names": settings.LANGUAGES,
        # 現在の言語コード
        "language": session["language"]
        if "language" in settings.BABEL_SUPPORTED_LOCALES
        else "ja",
        "is_translated": is_translated(
            request.path, getattr(request, "LANGUAGE_CODE", "ja")
        ),
        "current_url": request.url,
        "last_updated": settings.LAST_UPDATED,
        "is_latest_year": is_latest_year_flag,
        "is_early_access": is_early_access_flag,
        "is_gbb_ended": is_gbb_ended(year),
        "is_local": settings.IS_LOCAL,
        "is_pull_request": settings.IS_PULL_REQUEST,
        "scroll": request.args.get("scroll", ""),
    }


def get_locale():
    """
    ユーザーの言語設定を取得します。
    利用可能な言語の中から、セッションに保存された言語を優先的に返します。
    セッションに言語が保存されていない場合は、リクエストの受け入れ言語の中から最適な言語を選択します。

    Returns:
        str: ユーザーの言語設定
    """
    # セッションに言語が設定されているか確認
    if "language" not in session:
        best_match = request.accept_languages.best_match(
            settings.BABEL_SUPPORTED_LOCALES
        )
        session["language"] = best_match if best_match else "ja"
    return session["language"]
