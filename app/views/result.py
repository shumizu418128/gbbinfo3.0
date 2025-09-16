from collections import defaultdict

from flask import abort, redirect, render_template, request

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator


# MARK: 大会結果
def result_view(year: int):
    """指定された年の大会結果ページを表示するビュー関数。

    Args:
        year (int): 結果を表示する対象の年。

    Returns:
        flask.Response: 結果ページのHTMLを返す。条件によってはリダイレクトする。

    Notes:
        - 2013年から2016年は非対応のため、トップページにリダイレクトされる。
        - クエリパラメータ 'category' でカテゴリを指定する。無効な場合はデフォルトで"Loopstation"にリダイレクト。
        - カテゴリごとにトーナメント制または順位制の結果を取得し、テンプレートに渡す。
        - 結果データが存在しない場合は空データでページを表示する。
    """
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
    # supabaseから取得失敗した場合、500エラーを返す
    if not year_data:
        abort(500)

    # 以降、supabaseと接続ができるとみなす

    all_categories_for_year_id = year_data["categories"].tolist()[0]

    # idから名前を取得
    category_data = supabase_service.get_data(
        table="Category",
        columns=["id", "name", "is_team"],
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
    category_is_team_numpy_bool = category_data[category_data["name"] == category][
        "is_team"
    ].values[0]
    category_is_team = bool(category_is_team_numpy_bool)

    # データ取得
    # まずトーナメント制のデータを取得
    result_type = "tournament"
    result_data = supabase_service.get_data(
        table="TournamentResult",
        columns=["round", "winner", "loser"],
        join_tables={
            "winner:Participant!TournamentResult_winner_fkey": ["id", "name"],
            "loser:Participant!TournamentResult_loser_fkey": ["id", "name"],
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
                "Participant": ["id", "name"],
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
                    "id": result["Participant"]["id"],
                    "name": result["Participant"]["name"].upper(),
                }
            )

    elif result_type == "tournament":
        for result in result_data:
            result_defaultdict[result["round"]].append(
                {
                    "winner": {
                        "id": result["winner"]["id"],
                        "name": result["winner"]["name"].upper(),
                    },
                    "loser": {
                        "id": result["loser"]["id"],
                        "name": result["loser"]["name"].upper(),
                    },
                }
            )

    # defaultdictはhtmlで扱えないので辞書に変換
    result_dict = dict(result_defaultdict)

    # テンプレートに渡すデータ
    context = {
        "category": category,
        "category_is_team": category_is_team,
        "result_data": result_dict,
        "result_type": result_type,
        "all_category": all_category_names,
    }

    return render_template("common/result.html", **context)
