from collections import defaultdict

from flask import redirect, render_template, request

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator


def result_view(year: int):
    # 2013-2016は非対応
    if 2013 <= year <= 2016:
        return redirect(f"/{year}/top")

    # クエリパラメータ
    category = request.args.get("category")

    # その年のカテゴリ一覧を取得
    year_data = supabase_service.get_data(
        table="Year",
        columns=["categories"],
        filters={
            "year": year,
        },
        pandas=True,
    )
    all_categories_for_year_id = year_data["categories"].tolist()[0]

    # idから名前を取得
    category_data = supabase_service.get_data(
        table="Category",
        columns=["id", "name"],
        filters={
            f"id__{Operator.IN_}": all_categories_for_year_id,
        },
        pandas=True,
    )
    all_category_names = category_data["name"].tolist()

    # 引数の正当性チェック
    # 問題がある場合デフォルト値にしてリダイレクト
    if category not in all_category_names:
        category = "Loopstation"
        return redirect(f"/{year}/result?category={category}")

    # カテゴリIDを取得
    category_id = int(category_data[category_data["name"] == category]["id"].values[0])

    # データ取得
    # まずトーナメント制のデータを取得
    result_type = "tournament"
    result_data = supabase_service.get_data(
        table="TournamentResult",
        columns=["round", "winner", "loser"],
        join_tables={
            "winner:Participant!TournamentResult_winner_fkey": ["name"],
            "loser:Participant!TournamentResult_loser_fkey": ["name"],
        },
        filters={
            "year": year,
            "category": category_id,
        },
    )

    # ない場合、順位制のデータを取得
    if len(result_data) == 0:
        result_type = "ranking"
        result_data = supabase_service.get_data(
            table="RankingResult",
            columns=["round", "participant", "rank"],
            join_tables={
                "Participant": ["name"],
            },
            filters={
                "year": year,
                "category": category_id,
            },
        )

    # 両方ない場合、データなしとして扱う
    if len(result_data) == 0:
        context = {
            "year": year,
            "category": category,
            "result_data": [],
            "result_type": "",
            "all_category": all_category_names,
        }
        return render_template("common/result.html", **context)

    result_defaultdict = defaultdict(list)

    # 順位制かトーナメント制かを判定
    if result_type == "ranking":
        for result in result_data:
            if result["round"] is None:
                result["round"] = "Overall"
            result_defaultdict[result["round"]].append(
                {
                    "rank": result["rank"],
                    "name": result["Participant"]["name"].upper(),
                }
            )

    elif result_type == "tournament":
        for result in result_data:
            result_defaultdict[result["round"]].append(
                {
                    "winner": result["winner"]["name"].upper(),
                    "loser": result["loser"]["name"].upper(),
                }
            )

    # defaultdictはhtmlで扱えないので辞書に変換
    result_dict = dict(result_defaultdict)

    # テンプレートに渡すデータ
    context = {
        "category": category,
        "result_data": result_dict,
        "result_type": result_type,
        "all_category": all_category_names,
    }

    return render_template("common/result.html", **context)
