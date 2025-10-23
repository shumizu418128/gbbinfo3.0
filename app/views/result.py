from collections import defaultdict

from flask import abort, redirect, render_template, request

from app.config.config import MULTI_COUNTRY_TEAM_ISO_CODE
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
    try:
        year_data = supabase_service.get_data(
            table="Year",
            columns=["categories"],
            filters={
                "year": year,
            },
            timeout=0,
            pandas=True,
            raise_error=True,
        )
    except Exception:
        abort(500)

    all_categories_for_year_id = year_data["categories"].tolist()[0]

    # idから名前を取得
    try:
        category_data = supabase_service.get_data(
            table="Category",
            columns=["id", "name", "is_team"],
            filters={
                f"id__{Operator.IN_}": all_categories_for_year_id,
            },
            pandas=True,
            raise_error=True,
        )
    except Exception:
        abort(500)

    # カテゴリがない場合、まだ発表前なので空データで早期リターン
    if category_data.empty:
        context = {
            "category": "",
            "category_is_team": False,
            "result_data": [],
            "result_type": "",
            "all_category": [],
        }
        return render_template("common/result.html", **context)

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
    try:
        result_data = supabase_service.get_data(
            table="TournamentResult",
            columns=["round", "winner", "loser"],
            join_tables={
                "winner:Participant!TournamentResult_winner_fkey": [
                    "id",
                    "name",
                    "Country(iso_alpha2, iso_code)",
                    "ParticipantMember(Country(iso_alpha2))",
                ],
                "loser:Participant!TournamentResult_loser_fkey": [
                    "id",
                    "name",
                    "Country(iso_alpha2, iso_code)",
                    "ParticipantMember(Country(iso_alpha2))",
                ],
            },
            filters={
                "year": year,
                "category": category_id,
            },
            raise_error=True,
        )

        # ない場合、順位制のデータを取得
        if len(result_data) == 0:
            result_type = "ranking"
            result_data = supabase_service.get_data(
                table="RankingResult",
                columns=["round", "participant", "rank"],
                join_tables={
                    "Participant": [
                        "id",
                        "name",
                        "Country(iso_alpha2, iso_code)",
                        "ParticipantMember(Country(iso_alpha2))",
                    ],
                },
                filters={
                    "year": year,
                    "category": category_id,
                },
                raise_error=True,
            )
    except Exception:
        abort(500)

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
            iso_alpha2_list = []
            if result["round"] is None:
                result["round"] = "Overall"
            iso_code = result["Participant"]["Country"]["iso_code"]

            if iso_code == MULTI_COUNTRY_TEAM_ISO_CODE:
                for member in result["Participant"]["ParticipantMember"]:
                    iso_alpha2_list.append(member["Country"]["iso_alpha2"])
                iso_alpha2_list = sorted(list(set(iso_alpha2_list)))
            else:
                iso_alpha2_list = [result["Participant"]["Country"]["iso_alpha2"]]

            result_defaultdict[result["round"]].append(
                {
                    "rank": result["rank"],
                    "id": result["Participant"]["id"],
                    "name": result["Participant"]["name"].upper(),
                    "iso_alpha2": iso_alpha2_list,
                }
            )

    elif result_type == "tournament":
        for result in result_data:
            # 勝者の国コードを取得
            winner_iso_alpha2_list = []
            if result["winner"]["Country"]["iso_code"] == MULTI_COUNTRY_TEAM_ISO_CODE:
                for member in result["winner"]["ParticipantMember"]:
                    winner_iso_alpha2_list.append(member["Country"]["iso_alpha2"])
                winner_iso_alpha2_list = sorted(list(set(winner_iso_alpha2_list)))
            else:
                winner_iso_alpha2_list = [result["winner"]["Country"]["iso_alpha2"]]

            # 敗者の国コードを取得
            loser_iso_alpha2_list = []
            if result["loser"]["Country"]["iso_code"] == MULTI_COUNTRY_TEAM_ISO_CODE:
                for member in result["loser"]["ParticipantMember"]:
                    loser_iso_alpha2_list.append(member["Country"]["iso_alpha2"])
                loser_iso_alpha2_list = sorted(list(set(loser_iso_alpha2_list)))
            else:
                loser_iso_alpha2_list = [result["loser"]["Country"]["iso_alpha2"]]

            result_defaultdict[result["round"]].append(
                {
                    "winner": {
                        "id": result["winner"]["id"],
                        "name": result["winner"]["name"].upper(),
                        "iso_alpha2": winner_iso_alpha2_list,
                    },
                    "loser": {
                        "id": result["loser"]["id"],
                        "name": result["loser"]["name"].upper(),
                        "iso_alpha2": loser_iso_alpha2_list,
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
