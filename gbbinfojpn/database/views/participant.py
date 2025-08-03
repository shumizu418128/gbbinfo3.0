"""
参加者データ表示用ビュー
Supabaseから参加者データを取得し、htmlを返す
"""

from django.http import HttpRequest
from django.shortcuts import redirect, render

from gbbinfojpn.common.filter_eq import Operator
from gbbinfojpn.common.participant_edit import wildcard_rank_sort
from gbbinfojpn.database.models.supabase_client import supabase_service


def participants_view(request: HttpRequest):
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
    year_data = supabase_service.get_data(
        table="Year",
        columns=["year", "categories"],
        filters={f"categories__{Operator.IS_NOT}": None},
    )
    available_years = [item["year"] for item in year_data]

    # 年度を降順にソート
    available_years.sort(reverse=True)

    # 年度が有効か確認
    if param_year not in available_years:
        param_year = max(available_years)
        return redirect(
            f"/database/participants?category={param_category_name}&year={param_year}"
        )

    # その年のカテゴリ一覧を取得
    year_data_for_categories = supabase_service.get_data(
        table="Year",
        columns=["categories"],
        filters={
            "year": param_year,
        },
        pandas=True,
    )
    all_categories_for_year_id = year_data_for_categories["categories"].tolist()[0]

    # idから名前を取得
    category_data = supabase_service.get_data(
        table="Category",
        columns=["id", "name"],
        filters={
            f"id__{Operator.IN_}": all_categories_for_year_id,
        },
        pandas=True,
    )
    categories_for_year = category_data["name"].tolist()

    # カテゴリ名が有効か確認
    if param_category_name not in categories_for_year:
        param_category_name = "Loopstation"  # Loopを最優先に
        return redirect(
            f"/database/participants?category={param_category_name}&year={param_year}"
        )

    # カテゴリ名からidを取得
    param_category_id = int(
        category_data[category_data["name"] == param_category_name]["id"].values[0]
    )

    # 出場者データを取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["name", "category", "ticket_class", "is_cancelled", "iso_code"],
        join_tables={
            "Category": ["id", "name"],
            "Country": ["iso_code", "names"],
        },
        filters={
            "year": param_year,
            "category": param_category_id,
        },
    )
    participants_data.sort(
        key=lambda x: (
            x["is_cancelled"],  # キャンセルした人は下
            x["iso_code"] == 0,  # 出場者未定枠は下
            "Wildcard" in x["ticket_class"],  # Wildcard通過者は下
            wildcard_rank_sort(x),  # Wildcardのランキング順にする
            "GBB" not in x["ticket_class"],  # GBBによるシードは上
        )
    )

    language = "ja"

    for participant in participants_data:
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]
        participant.pop("Category")

        # 国名を取り出す
        participant["country"] = participant["Country"]["names"][language]
        participant.pop("Country")

    # テンプレートに渡すデータ
    context = {
        "participants_data": participants_data,
        "available_categories": categories_for_year,
        "available_years": available_years,
        "selected_category_name": param_category_name,
        "selected_year": param_year,
    }

    return render(request, "database/participants.html", context)
