from django.http import HttpResponseRedirect
from django.shortcuts import render

# TODO: available_yearsについて、DBから自動取得
# TODO: gbbinfojpn.databaseは使わない


def redirect_to_latest_top(request):
    available_years = []
    latest_year = available_years[-1]
    return HttpResponseRedirect(f"/{latest_year}/top")


def common(request, year, content):
    """
    共通のビュー処理。特定のコンテンツを年度ごとに表示する。

    Args:
        request (HttpRequest): リクエストオブジェクト
        year (int): 年度
        content (str): 表示するコンテンツ

    Returns:
        HttpResponse: レンダリングされたテンプレート
    """
    # ここでは、contentに応じた処理を行うことができます。
    # 例えば、contentが"top"ならトップページのデータを取得して表示するなど。

    context = {
        "year": year,
        "content": content,
    }

    return render(request, f"app/{content}.html", context)
