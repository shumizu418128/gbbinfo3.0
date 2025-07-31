"""
参加者データ表示用ビュー
Supabaseから参加者データを取得し、htmlを返す
"""

from django.http import HttpRequest
from django.shortcuts import redirect, render

from gbbinfojpn.common.filter_eq import Operator
from gbbinfojpn.database.models.supabase_client import supabase_service


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
    param_category_id = int(category_data[category_data["name"] == param_category_name]["id"].values[0])

    # 出場者データを取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["name", "category", "ticket_class", "is_cancelled"],
        order_by="is_cancelled",  # キャンセルしていない人を上に
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["participant", "name"],
            "Country": ["iso_code", "names"],
        },
        filters={
            "year": param_year,
            "category": param_category_id,
        },
    )

    # 言語を取得
    language = request.LANGUAGE_CODE

    for participant in participants_data:
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]
        participant.pop("Category")

        # メンバー名を取り出す
        participant["members"] = ", ".join(
            member["name"].upper() for member in participant["ParticipantMember"]
        )
        participant.pop("ParticipantMember")

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
