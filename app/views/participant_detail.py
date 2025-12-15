import random
from datetime import datetime
from urllib.parse import quote

from flask import redirect, render_template, request, session

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator
from app.util.participant_edit import edit_country_data, wildcard_rank_sort


# MARK: 出場者詳細
def participant_detail_view(participant_id, mode):
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
    language = session["language"]

    # ========================================
    # 2. 出場者データの取得
    # ========================================
    if mode == "team_member":
        beatboxer_data = supabase_service.get_data(
            table="ParticipantMember",
            columns=["id", "participant", "name", "iso_code"],
            join_tables={
                "Country": ["iso_code", "names", "iso_alpha2"],
                "Participant": [
                    "id",
                    "name",
                    "year",
                    "is_cancelled",
                    "ticket_class",
                    "Category(id, name)",
                ],
            },
            filters={"id": participant_id},
        )
    else:
        beatboxer_data = supabase_service.get_data(
            table="Participant",
            columns=[
                "id",
                "name",
                "year",
                "iso_code",
                "ticket_class",
                "is_cancelled",
            ],
            join_tables={
                "Country": ["iso_code", "names", "iso_alpha2"],
                "Category": ["id", "name"],
                "ParticipantMember": ["id", "name", "Country(names, iso_alpha2)"],
            },
            filters={"id": participant_id},
        )

    # データがない場合、出場者ページへリダイレクト
    if len(beatboxer_data) == 0 or beatboxer_data[0]["iso_code"] == 0:
        year = datetime.now().year
        return redirect(f"/{year}/participants")

    # ========================================
    # 3. 出場者データの正規化
    # ========================================
    beatboxer_detail = beatboxer_data[0]

    # 名前を大文字に変換
    beatboxer_detail["name"] = beatboxer_detail["name"].upper()

    # 設定言語に合わせて国名を取得
    beatboxer_detail = edit_country_data(beatboxer_detail, language)

    # team_memberモードの場合、Participantからフィールドを展開
    if mode == "team_member":
        participant = beatboxer_detail["Participant"]
        participant["name"] = participant["name"].upper()
        beatboxer_detail["year"] = participant["year"]
        beatboxer_detail["is_cancelled"] = participant["is_cancelled"]
        beatboxer_detail["ticket_class"] = participant["ticket_class"]
        beatboxer_detail["category"] = participant["Category"]["name"]
        beatboxer_detail["category_id"] = participant["Category"]["id"]
    else:
        # single/teamモードの場合、Categoryからフィールドを取得
        category = beatboxer_detail["Category"]
        beatboxer_detail["category"] = category["name"]
        beatboxer_detail["category_id"] = category["id"]

    # ParticipantMemberの名前と国名を処理
    for member in beatboxer_detail.get("ParticipantMember", []):
        member["name"] = member["name"].upper()
        member["country"] = member["Country"]["names"][language]
        member["iso_alpha2"] = [member["Country"]["iso_alpha2"]]

    # ========================================
    # 4. 過去の出場履歴の取得
    # ========================================
    # Participantテーブルから過去の出場履歴を取得
    past_participation_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "year", "is_cancelled", "category"],
        order_by="year",
        join_tables={
            "Category": ["name", "is_team"],
            "ParticipantMember": ["id"],
        },
        filters={
            f"name__{Operator.MATCH_IGNORE_CASE}": beatboxer_detail["name"],
        },
    )

    # ParticipantMemberテーブルから過去の出場履歴を取得
    past_participation_member_data = supabase_service.get_data(
        table="ParticipantMember",
        columns=["name"],
        join_tables={
            "Participant": [
                "id",
                "name",
                "year",
                "is_cancelled",
                "Category(name, id)",
            ],
        },
        filters={
            f"name__{Operator.MATCH_IGNORE_CASE}": beatboxer_detail["name"],
        },
    )

    # ========================================
    # 5. 過去の出場履歴の正規化
    # ========================================
    past_data = []

    # MATCH_IGNORE_CASE演算子は大文字小文字を区別しない部分一致であるため、完全一致の確認を行う
    for data in past_participation_data:
        if data["name"].upper() == beatboxer_detail["name"]:
            past_participation_mode = (
                "team" if data["Category"]["is_team"] else "single"
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
                    "category_id": past_participation_member["Participant"]["Category"][
                        "id"
                    ],
                    "is_cancelled": past_participation_member["Participant"][
                        "is_cancelled"
                    ],
                    "mode": "team",
                }
            )

    past_data.sort(key=lambda x: (x["year"], x["category_id"]))

    # ========================================
    # 6. 過去の出場年度の抽出（最大4年分）
    # ========================================
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

    # ========================================
    # 7. 同年・同部門の出場者一覧の取得
    # ========================================
    category_id = beatboxer_detail["category_id"]

    same_year_category_participants = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "is_cancelled", "ticket_class", "iso_code"],
        join_tables={
            "Country": ["names", "iso_alpha2"],
            "ParticipantMember": ["id", "name", "Country(names, iso_alpha2)"],
        },
        filters={
            "year": beatboxer_detail["year"],
            "category": category_id,
        },
    )

    # ========================================
    # 8. 同年・同部門の出場者一覧の加工
    # ========================================
    same_year_category_edited = []

    for participant in same_year_category_participants:
        # 名前は大文字に変換
        participant["name"] = participant["name"].upper()

        # 設定言語に合わせて国名を設定
        participant = edit_country_data(participant, language)

        same_year_category_edited.append(participant)

    # ランダムで最大5人を選ぶ
    same_year_category_edited = random.sample(
        same_year_category_edited, min(5, len(same_year_category_edited))
    )

    # ソート: キャンセル→未定→Wildcard→ランキング→GBBシード
    same_year_category_edited.sort(
        key=lambda x: (
            x["is_cancelled"],  # キャンセルした人は下
            x["iso_code"] == 0,  # 出場者未定枠は下
            "Wildcard" in x["ticket_class"],  # Wildcard通過者は下
            wildcard_rank_sort(x),  # Wildcardのランキング順にする
            "GBB" not in x["ticket_class"],  # GBBによるシードは上
        )
    )

    # ========================================
    # 9. テンプレートコンテキストの作成
    # ========================================
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

    return render_template("participant_detail/participant_detail.html", **context)


# MARK: リダイレクト
def participant_detail_deprecated_view():
    """
    参加者詳細情報を表示する (deprecated)。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        HttpResponse: レンダリングされたテンプレート
    """
    participant_id = request.args.get("id", type=int)
    mode = request.args.get("mode", type=str)

    allowed_modes = {"single", "team", "team_member"}
    if mode not in allowed_modes:
        year = datetime.now().year
        return redirect(f"/{year}/participants")

    # パラメータが欠落している場合は直接参加者一覧ページへリダイレクトする
    if participant_id is None or mode is None:
        year = datetime.now().year
        return redirect(f"/{year}/participants")

    return redirect(f"/participant_detail/{participant_id}/{mode}")
