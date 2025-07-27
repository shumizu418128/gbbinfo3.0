from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.common.filter_eq import Operator


def redirect_to_latest_top(request: HttpRequest):
    year_data = supabase_service.get_data(
        table="Year",
        columns=["year"],
        filters={f"categories__{Operator.IS_NOT}": None},
    )
    available_years = [item["year"] for item in year_data]
    available_years.sort(reverse=True)
    latest_year = available_years[0]
    return HttpResponseRedirect(f"/{latest_year}/top")


def common(request: HttpRequest, year: int, content: str):
    """
    共通のビュー処理。特定のコンテンツを年度ごとに表示する。

    Args:
        request (HttpRequest): リクエストオブジェクト
        year (int): 年度
        content (str): 表示するコンテンツ

    Returns:
        HttpResponse: レンダリングされたテンプレート
    """
    return render(request, f"{year}/{content}.html")
