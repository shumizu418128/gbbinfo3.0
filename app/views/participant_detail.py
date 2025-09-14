import random
from datetime import datetime
from urllib.parse import quote

from flask import redirect, render_template, request, session

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator
from app.util.participant_edit import team_multi_country, wildcard_rank_sort

MULTI_COUNTRY_TEAM_ISO_CODE = 9999


# MARK: 出場者詳細
def participant_detail_view():
    """
    出場者詳細ページのビュー関数。

    リクエストから出場者ID（id）とモード（mode）を取得し、該当する出場者の詳細情報を取得して返します。
    チームメンバーの場合はParticipantMemberテーブルから、個人またはチームの場合はParticipantテーブルから情報を取得します。
    データが存在しない場合は参加者ページにリダイレクトします。

    Returns:
        Response: 出場者詳細ページのHTMLレスポンス、または参加者ページへのリダイレクト。

    Raises:
        なし（id, modeが無い場合やデータが存在しない場合は参加者ページにリダイレクトする）
    """
    try:
        id = request.args["id"]  # 出場者ID
        mode = request.args["mode"]  # single, team, team_member
    except KeyError:
        # id, modeが無い場合、出場者ページへリダイレクト
        year = datetime.now().year
        return redirect(f"/{year}/participants")

    # チームメンバーの場合、情報を取得
    if mode == "team_member":
        beatboxer_data = supabase_service.get_data(
            table="ParticipantMember",
            columns=["id", "participant", "name"],
            join_tables={
                "Country": ["iso_code", "names"],
                "Participant": [
                    "id",
                    "name",
                    "year",
                    "category",
                    "is_cancelled",
                ],
            },
            filters={
                "id": id,
            },
        )
        # データがない場合、出場者ページへリダイレクト
        if len(beatboxer_data) == 0:
            year = datetime.now().year
            return redirect(f"/{year}/participants")

        beatboxer_detail = beatboxer_data[0]

        # 名前は大文字に変換
        beatboxer_detail["name"] = beatboxer_detail["name"].upper()
        beatboxer_detail["Participant"]["name"] = beatboxer_detail["Participant"][
            "name"
        ].upper()

        # 設定言語に合わせて国名を取得
        language = session["language"]
        beatboxer_detail["country"] = beatboxer_detail["Country"]["names"][language]
        beatboxer_detail.pop("Country")

        # メンバーの情報に無い情報を追加
        beatboxer_detail["year"] = beatboxer_detail["Participant"]["year"]
        beatboxer_detail["is_cancelled"] = beatboxer_detail["Participant"][
            "is_cancelled"
        ]

    # 1人部門 or チーム部門のチームについての情報を取得
    else:
        beatboxer_data = supabase_service.get_data(
            table="Participant",
            columns=[
                "id",
                "name",
                "year",
                "category",
                "iso_code",
                "ticket_class",
                "is_cancelled",
            ],
            join_tables={
                "Country": ["iso_code", "names"],
                "Category": ["id", "name"],
                "ParticipantMember": ["id", "name", "Country(names)"],
            },
            filters={
                "id": id,
            },
        )

        # データがない場合、出場者ページへリダイレクト
        if len(beatboxer_data) == 0:
            year = datetime.now().year
            return redirect(f"/{year}/participants")

        beatboxer_detail = beatboxer_data[0]

        # 名前は大文字に変換
        beatboxer_detail["name"] = beatboxer_detail["name"].upper()

        # 設定言語に合わせて国名を取得
        language = session["language"]

        # 複数国籍のチームの場合、国名をまとめる
        if beatboxer_detail["iso_code"] == MULTI_COUNTRY_TEAM_ISO_CODE:
            beatboxer_detail = team_multi_country(beatboxer_detail, language)

        # 1国籍のチームの場合、国名を取得
        else:
            beatboxer_detail["country"] = beatboxer_detail["Country"]["names"][language]
            beatboxer_detail.pop("Country")

        # 部門名を取得
        beatboxer_detail["category"] = beatboxer_detail["Category"]["name"]

        # チームメンバーの国名を取得
        if len(beatboxer_detail["ParticipantMember"]) > 0:
            for member in beatboxer_detail["ParticipantMember"]:
                member["country"] = member["Country"]["names"][language]
                member["name"] = member["name"].upper()

    # 過去の出場履歴を取得
    past_participation_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "year", "is_cancelled", "category"],
        order_by="year",
        join_tables={
            "Category": ["name"],
            "ParticipantMember": ["id"],
        },
        filters={
            f"name__{Operator.MATCH_IGNORE_CASE}": beatboxer_detail["name"],
        },
    )
    past_participation_member_data = supabase_service.get_data(
        table="ParticipantMember",
        columns=["name"],
        join_tables={
            "Participant": [
                "id",
                "name",
                "year",
                "is_cancelled",
                "Category(name)",
                "category",
            ],
        },
        filters={
            f"name__{Operator.MATCH_IGNORE_CASE}": beatboxer_detail["name"],
        },
    )

    past_data = []

    # MATCH_IGNORE_CASE演算子は大文字小文字を区別しない部分一致であるため、完全一致の確認を行う
    for data in past_participation_data:
        if data["name"].upper() == beatboxer_detail["name"]:
            past_participation_mode = (
                "single" if len(data["ParticipantMember"]) == 0 else "team"
            )
            past_data.append(
                {
                    "id": data["id"],
                    "year": data["year"],
                    "name": data["name"].upper(),
                    "category": data["Category"]["name"],
                    "category_id": data["category"],
                    "is_cancelled": data["is_cancelled"],
                    "mode": past_participation_mode,
                }
            )
    for past_participation_member in past_participation_member_data:
        if past_participation_member["name"].upper() == beatboxer_detail["name"]:
            past_data.append(
                {
                    "id": past_participation_member["Participant"]["id"],
                    "year": past_participation_member["Participant"]["year"],
                    "name": past_participation_member["Participant"]["name"].upper(),
                    "category": past_participation_member["Participant"]["Category"][
                        "name"
                    ],
                    "category_id": past_participation_member["Participant"]["category"],
                    "is_cancelled": past_participation_member["Participant"][
                        "is_cancelled"
                    ],
                    "mode": "team",
                }
            )
    past_data.sort(key=lambda x: (x["year"], x["category_id"]))

    # 過去の出場履歴（年度）を取得
    past_year_participation = set()
    for data in past_data:
        past_year_participation.add(data["year"])

    # 2013-2016は除外
    exception_year = {2013, 2014, 2015, 2016}
    past_year_participation -= exception_year

    # 多い場合は、ページの表示対象年度を除外 最大4年分
    if len(past_year_participation) > 4:
        past_year_participation -= {beatboxer_detail["year"]}

    # 並び替え
    past_year_participation = list(past_year_participation)
    past_year_participation.sort(reverse=True)

    # 最大4年分
    if len(past_year_participation) > 4:
        past_year_participation = past_year_participation[:4]

    # 対象Beatboxerと同じ年・部門の出場者一覧を取得
    # 部門を調べる
    if mode == "team_member":
        category_id = beatboxer_detail["Participant"]["category"]
    else:
        category_id = beatboxer_detail["Category"]["id"]

    same_year_category_participants = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "is_cancelled", "ticket_class", "iso_code"],
        join_tables={
            "Country": ["names"],
            "ParticipantMember": ["id", "name", "Country(names)"],
        },
        filters={
            "year": beatboxer_detail["year"],
            "category": category_id,
        },
    )

    same_year_category_edited = []
    for participant in same_year_category_participants:
        participant["name"] = participant["name"].upper()
        if participant["iso_code"] == MULTI_COUNTRY_TEAM_ISO_CODE:
            participant = team_multi_country(participant, language)
        else:
            participant["country"] = participant["Country"]["names"][language]
            participant.pop("Country")
        same_year_category_edited.append(participant)

    # ランダムで最大5人を選ぶ
    same_year_category_edited = random.sample(
        same_year_category_edited, min(5, len(same_year_category_edited))
    )
    same_year_category_edited.sort(
        key=lambda x: (
            x["is_cancelled"],  # キャンセルした人は下
            x["iso_code"] == 0,  # 出場者未定枠は下
            "Wildcard" in x["ticket_class"],  # Wildcard通過者は下
            wildcard_rank_sort(x),  # Wildcardのランキング順にする
            "GBB" not in x["ticket_class"],  # GBBによるシードは上
        )
    )

    same_year_category_mode = "single" if mode == "single" else "team"
    ai_search_query = quote(beatboxer_detail["name"] + " beatbox")

    context = {
        "beatboxer_detail": beatboxer_detail,
        "mode": mode,
        "past_participation_data": past_data,
        "same_year_category_participants": same_year_category_edited,
        "same_year_category_mode": same_year_category_mode,
        "ai_search_query": ai_search_query,
        "past_year_participation": past_year_participation,
    }

    return render_template("others/participant_detail.html", **context)
