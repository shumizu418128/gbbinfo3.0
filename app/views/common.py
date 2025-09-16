import os
from datetime import datetime

from flask import redirect, render_template
from jinja2 import TemplateNotFound

from app.context_processors import get_available_years


# MARK: トップ遷移
def top_redirect_view():
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


# MARK: 共通ビュー
def content_view(year: int, content: str):
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
        return render_template(f"{year}/{content_basename}.html")
    except TemplateNotFound:
        return not_found_page_view()


# MARK: 2022ビュー
def content_2022_view(content: str):
    """
    2022年の特定のコンテンツを表示するビュー。

    Args:
        request (HttpRequest): リクエストオブジェクト
        content (str): 表示するコンテンツ

    Returns:
        HttpResponse: レンダリングされたテンプレート
    """
    content_basename = os.path.basename(content)
    if content_basename != "top":
        return redirect("/2022/top")

    try:
        return render_template(f"2022/{content_basename}.html")
    except TemplateNotFound:
        return render_template("/common/404.html"), 404


# MARK: others
def other_content_view(content: str):
    """
    その他のコンテンツを表示する。
    """
    content_basename = os.path.basename(content)

    try:
        return render_template(f"others/{content_basename}.html")
    except TemplateNotFound:
        return render_template("/common/404.html"), 404


# MARK: 404
def not_found_page_view():
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
    return render_template("common/404.html", context=context), 404


# MARK: 500
def internal_server_error_view():
    """
    500ページを表示する。
    """
    return render_template("common/500.html"), 500
