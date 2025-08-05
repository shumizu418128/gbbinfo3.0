import os
from datetime import datetime

from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist

from gbbinfojpn.app.context_processors import get_available_years


def top_redirect_view(request: HttpRequest):
    """
    最新の年度のトップページへリダイレクトするビュー。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        redirect: 最新年度のトップページへのリダイレクト
    """
    available_years = get_available_years()
    if datetime.now().year in available_years:
        latest_year = datetime.now().year
    else:
        latest_year = max(available_years)
    return redirect(f"/{latest_year}/top")


def content_view(request: HttpRequest, year: int, content: str):
    """
    共通のビュー処理。特定のコンテンツを年度ごとに表示する。

    Args:
        request (HttpRequest): リクエストオブジェクト
        year (int): 年度
        content (str): 表示するコンテンツ

    Returns:
        HttpResponse: レンダリングされたテンプレート
    """
    content_basename = os.path.basename(content)

    # 2013-2016年の場合、topページ以外はリダイレクト
    if 2013 <= year <= 2016 and content_basename != "top":
        return redirect(f"/{year}/top")

    try:
        return render(request, f"{year}/{content_basename}.html")
    except TemplateDoesNotExist:
        return not_found_page_view(request)


def other_content_view(request: HttpRequest, content: str):
    """
    その他のコンテンツを表示する。
    """
    content_basename = os.path.basename(content)

    try:
        return render(request, f"others/{content_basename}.html")
    except TemplateDoesNotExist:
        return not_found_page_view(request)


def not_found_page_view(request: HttpRequest, exception=None):
    """
    404ページを表示する。

    Args:
        request (HttpRequest): リクエストオブジェクト
        year (int): 年度

    Returns:
        HttpResponse: 404ページのレンダリング
    """
    context = {
        "is_translated": True,
    }
    return render(request, "common/404.html", context, status=404)
