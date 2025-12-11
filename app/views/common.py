import os
from datetime import datetime, timedelta, timezone

from flask import jsonify, redirect, render_template
from flask_babel import format_datetime
from jinja2 import TemplateNotFound

from app.context_processors import get_available_years
from app.models.spreadsheet_client import spreadsheet_service


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


# MARK: timetable
def time_schedule_view(year: int):
    """
    タイムテーブルを表示するビュー。
    """
    return redirect(f"/{year}/timetable")


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


# MARK: travel
def travel_content_view(content: str):
    """
    旅行関連のコンテンツを表示する。
    """
    content_basename = os.path.basename(content)

    try:
        return render_template(f"travel/{content_basename}.html")
    except TemplateNotFound:
        return redirect("/travel/top")


# MARK: notice
def notice_view():
    """
    お知らせコンテンツを表示する。
    """
    notice, timestamp_str = "", ""
    try:
        notice, timestamp_str = spreadsheet_service.get_notice()
    except Exception:
        pass

    if notice == "" or timestamp_str == "":
        return jsonify({"notice": "", "timestamp": ""})

    timestamp_datetime = datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S")

    # 日本時間（JST）として扱う
    jst = timezone(timedelta(hours=9))
    timestamp_datetime = timestamp_datetime.replace(tzinfo=jst)
    formatted_timestamp = format_datetime(timestamp_datetime, "full")

    return jsonify({"notice": notice, "timestamp": formatted_timestamp})


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
    context = {
        "is_translated": True,
    }
    return render_template("common/500.html", context=context), 500
