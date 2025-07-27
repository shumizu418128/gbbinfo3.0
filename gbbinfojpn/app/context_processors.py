from datetime import datetime

from django.conf import settings
from django.http import HttpRequest


def get_available_years():
    # TODO: DBから自動取得できるようにする
    # TODO: gbbinfojpn.databaseは使わない
    # TODO: とったコードはcacheに入れる
    available_years = []

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
    # TODO: 翻訳ファイルがあるかどうかを判定する
    return False


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
        "available_langs": settings.LANGUAGES,
        "lang_names": settings.SUPPORTED_LANGUAGE_CODES,
        "last_updated": settings.LAST_UPDATED,
        "current_url": request.path,
        "language": request.session.get("language"),
        "is_translated": is_translated(request.path, request.session.get("language")),
        "is_latest_year": is_latest_year_flag,
        "is_early_access": is_early_access_flag,
        "is_local": settings.IS_LOCAL,
        "is_pull_request": settings.IS_PULL_REQUEST,
        "query_params": dict(request.GET),
        "year": year_str,
    }
