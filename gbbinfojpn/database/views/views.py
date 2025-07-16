"""
データ表示用ビュー
Supabaseからデータを取得し、htmlを返す
"""

from datetime import datetime

from django.http import HttpRequest
from django.shortcuts import redirect, render

from ..models.supabase_client import supabase_service
from . import cache


def sort_key(x):
    """
    参加者データのソートキーを生成する

    Args:
        x (dict): 参加者データの辞書

    Returns:
        tuple: ソート用のタプル (GBB優先度, iso code優先度, ワイルドカード優先度)
    """
    # GBBが含まれていれば最優先（0）、含まれていなければ1
    gbb_priority = 0 if "GBB" in x["ticket_class"] else 1
    # iso codeが0なら最下位（1）、それ以外は0
    iso_priority = (
        1 if x.get("Country", {}).get("iso_code", x.get("iso_code")) == 0 else 0
    )
    # Wildcardが含まれていれば最下位（1）、含まれていなければ0
    wildcard_priority = 1 if "Wildcard" in x["ticket_class"] else 0
    return (gbb_priority, iso_priority, wildcard_priority)


def participants(request: HttpRequest):
    """
    参加者一覧を表示するビュー

    クエリパラメータ category, year を受け取り、該当する参加者データをSupabaseから取得し、テンプレートに渡す。
    パラメータがない場合はデフォルト値でリダイレクトする。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        HttpResponse: 参加者一覧ページのレンダリング結果
    """

    # クエリパラメータがない場合はデフォルト値を設定
    if request.GET.get("category") is None or request.GET.get("year") is None:
        param_category_id = 1
        param_year = datetime.now().year
        return redirect(
            f"/database/participants?category={param_category_id}&year={param_year}"
        )

    # クエリパラメータを取得
    param_category_id = int(request.GET.get("category"))
    param_year = int(request.GET.get("year"))

    # JOINを使って参加者データと関連データを一度に取得
    # カテゴリがNULLの参加者を除外
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "ticket_class"],
        join_tables={
            "Country": ["names", "iso_code"],
            "Category": ["id", "name"],
        },
        filters={
            "year": param_year,
            "category": param_category_id,
        },
    )

    participants_data.sort(key=sort_key)

    language = "ja"

    # 取得したデータを処理
    for participant in participants_data:
        try:
            # 国名の処理
            country_names = participant["Country"]["names"]

            # 指定した言語の国名があればそれを使用、なければエラー
            participant["country"] = country_names[language]
        except KeyError:
            raise ValueError(
                f"国名（{language}）が見つかりません: {participant['iso_code']}"
            )
        participant.pop("Country")

    # 現在選択されている年度のカテゴリ（テンプレート表示用）
    # キャンセル年度フィルターを有効化
    categories_cache = cache.get_categories_for_year(param_year)
    years_cache = cache.get_category_by_year(filter_cancelled_year=True)

    available_years = list(years_cache.keys())

    context = {
        "participants_data": participants_data,
        "available_categories": categories_cache,
        "available_years": available_years,
        "selected_category_id": param_category_id,
        "selected_year": param_year,
        "title": "参加者一覧",
    }

    return render(request, "database/participants.html", context)


def test(request: HttpRequest):
    """
    テスト用：testテーブルのデータ一覧を表示するビュー

    Supabaseのtestテーブルからデータを取得し、テンプレートに渡す。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        HttpResponse: testテーブルデータ一覧ページのレンダリング結果
    """
    # Supabaseのtestテーブルからデータを直接取得
    test_data = supabase_service.get_data(
        table="test", columns=["id", "value", "created_at"]
    )

    context = {
        "test_data": test_data,
        "title": "Testテーブルデータ一覧",
    }

    return render(request, "database/test.html", context)
