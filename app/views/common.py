import os
from datetime import datetime

from flask import redirect, render_template
from jinja2 import TemplateNotFound
from sanic import response
from sanic.response import redirect as sanic_redirect
from sanic_ext import render

from app.context_processors import get_available_years


# MARK: トップ遷移
def top_redirect_view():
    """
    最新の年度のトップページへリダイレクトするビュー（同期版）。
    """
    available_years = get_available_years()
    if datetime.now().year in available_years:
        latest_year = datetime.now().year
    else:
        latest_year = max(available_years)
    return redirect(f"/{latest_year}/top")


async def top_redirect_view_async(request):
    """
    最新の年度のトップページへリダイレクトするビュー（非同期版）。
    """
    available_years = get_available_years()
    if datetime.now().year in available_years:
        latest_year = datetime.now().year
    else:
        latest_year = max(available_years)
    return sanic_redirect(f"/{latest_year}/top")


# MARK: 共通ビュー
def content_view(year: int, content: str):
    """
    共通のビュー処理（同期版）。特定のコンテンツを年度ごとに表示する。
    """
    content_basename = os.path.basename(content)

    # 2013-2016年の場合、topページ以外はリダイレクト
    if 2013 <= year <= 2016 and content_basename != "top":
        return redirect(f"/{year}/top")

    try:
        return render_template(f"{year}/{content_basename}.html")
    except TemplateNotFound:
        return not_found_page_view()


async def content_view_async(request, year: int, content: str):
    """
    共通のビュー処理（非同期版）。特定のコンテンツを年度ごとに表示する。
    """
    content_basename = os.path.basename(content)

    # 2013-2016年の場合、topページ以外はリダイレクト
    if 2013 <= year <= 2016 and content_basename != "top":
        return sanic_redirect(f"/{year}/top")

    try:
        # Sanicのテンプレート使用
        return await render(f"{year}/{content_basename}.html", request=request)
    except TemplateNotFound:
        return await not_found_page_view_async(request)


# MARK: 2022ビュー
def content_2022_view(content: str):
    """
    2022年の特定のコンテンツを表示するビュー（同期版）。
    """
    content_basename = os.path.basename(content)
    if content_basename != "top":
        return redirect("/2022/top")

    try:
        return render_template(f"2022/{content_basename}.html")
    except TemplateNotFound:
        return render_template("/common/404.html"), 404


async def content_2022_view_async(request, content: str):
    """
    2022年の特定のコンテンツを表示するビュー（非同期版）。
    """
    content_basename = os.path.basename(content)
    if content_basename != "top":
        return sanic_redirect("/2022/top")

    try:
        return await render(f"2022/{content_basename}.html")
    except TemplateNotFound:
        return await render("/common/404.html", status=404)


# MARK: others
def other_content_view(content: str):
    """
    その他のコンテンツを表示する（同期版）。
    """
    content_basename = os.path.basename(content)

    try:
        return render_template(f"others/{content_basename}.html")
    except TemplateNotFound:
        return render_template("/common/404.html"), 404


async def other_content_view_async(request, content: str):
    """
    その他のコンテンツを表示する（非同期版）。
    """
    content_basename = os.path.basename(content)

    try:
        return await render(f"others/{content_basename}.html")
    except TemplateNotFound:
        return await render("/common/404.html", status=404)


# MARK: 404
def not_found_page_view():
    """
    404ページを表示する（同期版）。
    """
    context = {
        "is_translated": True,
    }
    return render_template("common/404.html", context=context), 404


async def not_found_page_view_async(request):
    """
    404ページを表示する（非同期版）。
    """
    context = {
        "is_translated": True,
    }
    return await render("common/404.html", context=context, status=404)
