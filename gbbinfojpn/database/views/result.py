"""
結果データ表示用ビュー
Supabaseから結果データを取得し、htmlを返す
"""

from collections import defaultdict

from django.http import HttpRequest
from django.shortcuts import redirect, render

from gbbinfojpn.common.filter_eq import Operator
from gbbinfojpn.database.models.supabase_client import supabase_service


def results_view(request: HttpRequest):
    """
    結果一覧を表示するビュー

    クエリパラメータ category, year を受け取り、該当する結果データをSupabaseから取得し、テンプレートに渡す。
    カテゴリによって順位制（RankingResult）またはトーナメント制（TournamentResult）のデータを表示する。
    順位制かトーナメント制かは、実際のデータベースの内容から判断する。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        HttpResponse: 結果一覧ページのレンダリング結果
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
            f"/database/results?category={param_category_name}&year={param_year}"
        )

    # カテゴリ一覧
    categories_for_year_dict = supabase_service.get_data(
        table="Category",
        columns=["id", "name"],
    )
    for data in year_data:
        if data["year"] == param_year:
            categories_for_year_ids = data["categories"]
            break
    categories_for_year = [
        category["name"]
        for category in categories_for_year_dict
        if category["id"] in categories_for_year_ids
    ]

    # カテゴリ名が有効か確認
    if param_category_name not in categories_for_year:
        param_category_name = "Loopstation"  # Loopを最優先に
        return redirect(
            f"/database/results?category={param_category_name}&year={param_year}"
        )

    # カテゴリ名をIDに変換
    param_category_id = None
    for category in categories_for_year_dict:
        if category["name"] == param_category_name:
            param_category_id = category["id"]
            break
    if param_category_id is None:
        raise ValueError(f"カテゴリ名が見つかりません: {param_category_name}")

    # データベースの内容から順位制かトーナメント制かを判定
    # まずRankingResultテーブルにデータがあるかチェック
    ranking_data = supabase_service.get_data(
        table="RankingResult",
        columns=["round", "participant", "rank"],
        join_tables={
            "Participant": ["name"],
        },
        filters={
            "year": param_year,
            "category": param_category_id,
        },
    )

    # 次にTournamentResultテーブルにデータがあるかチェック
    tournament_data = supabase_service.get_data(
        table="TournamentResult",
        columns=["round", "winner", "loser"],
        join_tables={
            "winner:Participant!TournamentResult_winner_fkey": ["name"],
            "loser:Participant!TournamentResult_loser_fkey": ["name"],
        },
        filters={
            "year": param_year,
            "category": param_category_id,
        },
    )

    # 順位制かトーナメント制かを判定
    result_type = ""
    results_dict = {}

    if ranking_data:
        result_type = "ranking"
        results_data = defaultdict(list)
        for result in ranking_data:
            results_data[result["round"]].append(
                {
                    "rank": result["rank"],
                    "name": result["Participant"]["name"].upper(),
                }
            )
        results_dict = dict(results_data)

    elif tournament_data:
        result_type = "tournament"
        results_data = defaultdict(list)
        for result in tournament_data:
            results_data[result["round"]].append(
                {
                    "winner": result["winner"]["name"].upper(),
                    "loser": result["loser"]["name"].upper(),
                }
            )
        results_dict = dict(results_data)

    # テンプレートに渡すデータ
    context = {
        "results_data": results_dict,
        "result_type": result_type,
        "available_categories": categories_for_year,
        "available_years": available_years,
        "selected_category_name": param_category_name,
        "selected_year": param_year,
    }

    return render(request, "database/results.html", context)
