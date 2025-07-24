"""
データ表示用ビュー
Supabaseからデータを取得し、htmlを返す
"""

from django.http import HttpRequest
from django.shortcuts import redirect, render

from gbbinfojpn.database.models.supabase_client import supabase_service
from gbbinfojpn.database.views import cache  # cacheであることを明示


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

    # クエリパラメータを取得
    param_category_name = request.GET.get("category")
    param_year = int(request.GET.get("year", "-1"))

    # 年度一覧を取得
    available_years = list(
        cache.get_category_by_year(filter_cancelled_year=True).keys()
    )
    # 年度を降順にソート
    available_years.sort(reverse=True)

    # 年度が有効か確認
    if param_year not in available_years:
        param_year = max(available_years)
        return redirect(
            f"/database/participants?category={param_category_name}&year={param_year}"
        )

    # カテゴリ一覧
    categories_for_year_dict = cache.get_categories_for_year(param_year)
    categories_for_year = [
        category for dict in categories_for_year_dict for category in dict.values()
    ]

    # カテゴリ名が有効か確認
    if param_category_name not in categories_for_year:
        param_category_name = "Loopstation"  # Loopを最優先に
        return redirect(
            f"/database/participants?category={param_category_name}&year={param_year}"
        )

    # カテゴリ名をIDに変換
    param_category_id = cache.get_category_id_by_name(param_category_name)

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

    # ここでは日本語に設定
    # 本番ではsetting.SUPPORTED_LANGUAGE_CODESから取得
    language = "ja"

    # 取得したデータを処理
    for participant in participants_data:
        try:
            # 名前は全員大文字
            participant["name"] = participant["name"].upper()

            # 国名の処理
            country_names = participant["Country"]["names"]

            # 指定した言語の国名があればそれを使用、なければエラー
            participant["country"] = country_names[language]
        except KeyError:
            raise ValueError(
                f"国名（{language}）が見つかりません: {participant['iso_code']}"
            )
        participant.pop("Country")

    # テンプレートに渡すデータ
    context = {
        "participants_data": participants_data,
        "available_categories": categories_for_year,
        "available_years": available_years,
        "selected_category_name": param_category_name,
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
