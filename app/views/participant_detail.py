import random
from urllib.parse import quote

from flask import redirect, render_template, request, session

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator
from app.util.participant_edit import team_multi_country, wildcard_rank_sort


def participant_detail_view():
    try:
        id = request.args.get("id")  # 出場者ID
        mode = request.args.get("mode")  # single, team, team_member
    except KeyError:
        # id, modeが無い場合、ルートにリダイレクト
        return redirect("/")

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

        beatboxer_detail = beatboxer_data[0]

        # 名前は大文字に変換
        beatboxer_detail["name"] = beatboxer_detail["name"].upper()

        # 設定言語に合わせて国名を取得
        language = session["language"]

        # 複数国籍のチームの場合、国名をまとめる
        if beatboxer_detail["iso_code"] == 9999:
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
    for past_participation in past_participation_data:
        if past_participation["name"].upper() == beatboxer_detail["name"]:
            past_participation_mode = (
                "single"
                if len(past_participation["ParticipantMember"]) == 0
                else "team"
            )
            past_data.append(
                {
                    "id": past_participation["id"],
                    "year": past_participation["year"],
                    "name": past_participation["name"].upper(),
                    "category": past_participation["Category"]["name"],
                    "category_id": past_participation["category"],
                    "is_cancelled": past_participation["is_cancelled"],
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
        if participant["iso_code"] == 9999:
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
    genspark_query = quote(beatboxer_detail["name"] + " beatbox")

    context = {
        "beatboxer_detail": beatboxer_detail,
        "mode": mode,
        "past_participation_data": past_data,
        "same_year_category_participants": same_year_category_edited,
        "same_year_category_mode": same_year_category_mode,
        "genspark_query": genspark_query,
    }

    return render_template("others/participant_detail.html", context)
