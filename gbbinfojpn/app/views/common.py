from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.common.filter_eq import Operator


def top_redirect_view(request: HttpRequest):
    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
        filters={f"categories__{Operator.IS_NOT}": None},
    )
    available_years = [item["year"] for item in year_data]
    available_years.sort(reverse=True)
    latest_year = available_years[0]
    return HttpResponseRedirect(f"/{latest_year}/top")


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
    try:
        return render(request, f"{year}/{content}.html")
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
