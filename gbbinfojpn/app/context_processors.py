from datetime import datetime

from dateutil import parser
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.common.filter_eq import Operator


def get_available_years():
    """
    年度一覧を取得する関数。

    Returns:
        list: 利用可能な年度（降順）のリスト
    """
    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
        filters={f"categories__{Operator.IS_NOT}": None},
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
    return year == max(get_available_years()) or year == now


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

    # 常に英語のファイルを検証
    cache_key = "translated_urls_en"

    translated_urls = cache.get(cache_key)
    if translated_urls is None:
        raise Exception("translated_urlsがキャッシュされていません")

    return url in translated_urls


def is_gbb_ended(year):
    """
    指定された年度がGBB終了年度かを判定します。

    Args:
        year (int): 判定する年度

    Returns:
        bool: GBB終了年度の場合はTrue、それ以外はFalse
    """
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

    # タイムゾーンを考慮した現在時刻を取得
    now = timezone.now()

    # latest_year_ends_atがナイーブな場合はタイムゾーンを適用
    if latest_year_ends_at and timezone.is_naive(latest_year_ends_at):
        latest_year_ends_at = timezone.make_aware(latest_year_ends_at)

    return latest_year_ends_at < now


def common_variables(request: HttpRequest):
    """
    全テンプレートで共通して使う変数を返すコンテキストプロセッサ

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        dict: テンプレートに渡す共通変数
    """
    # 年度が公開範囲内か検証
    year_str = request.path.split("/")[1]
    is_latest_year_flag = None
    is_early_access_flag = None

    # 年度が最新 or 試験公開年度か検証
    try:
        year = int(year_str)
        is_latest_year_flag = is_latest_year(year)
        is_early_access_flag = is_early_access(year)
    except Exception:
        pass

    return {
        "available_years": get_available_years(),
        "lang_names": settings.LANGUAGES,
        "last_updated": settings.LAST_UPDATED,
        "current_url": request.path,
        "language": request.session.get("language"),
        "is_translated": is_translated(request.path, request.session.get("language")),
        "is_latest_year": is_latest_year_flag,
        "is_early_access": is_early_access_flag,
        "is_local": settings.IS_LOCAL,
        "is_pull_request": settings.IS_PULL_REQUEST,
        "is_gbb_ended": is_gbb_ended(year),
        "query_params": dict(request.GET),
        "year": year,
    }
