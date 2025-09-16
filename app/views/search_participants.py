from flask import abort, jsonify, request
from rapidfuzz import process

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator


# MARK: 出場者検索
def post_search_participants(year: int):
    """
    指定された年の参加者情報をキーワードで検索し、結果をJSONで返す。

    Args:
        year (int): 検索対象の年。

    Returns:
        flask.Response: 検索結果の参加者リストを含むJSONレスポンス。

    Notes:
        - 参加者名またはメンバー名にキーワードが部分一致（大文字小文字無視）した参加者を検索する。
        - 参加者情報には、id, name, category, ticket_class, is_cancelled, members, mode（single/team）が含まれる。
        - 参加者名・メンバー名は大文字に変換される。
        - 5件を超える場合は、キーワードとの類似度が高い上位5件のみ返す。
    """
    keyword = request.json.get("keyword")

    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "category", "ticket_class", "is_cancelled"],
        order_by="category",
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["id", "name"],
        },
        filters={"year": year, f"name__{Operator.MATCH_IGNORE_CASE}": f"%{keyword}%"},
    )

    # 検索結果が無い場合、キーワードの最初1文字のみで検索
    if not participants_data:
        participants_data = supabase_service.get_data(
            table="Participant",
            columns=["id", "name", "category", "ticket_class", "is_cancelled"],
            order_by="category",
            join_tables={
                "Category": ["id", "name"],
                "ParticipantMember": ["id", "name"],
            },
            filters={
                "year": year,
                f"name__{Operator.MATCH_IGNORE_CASE}": f"%{keyword[0]}%",
            },
        )

    # supabaseから取得失敗した場合、500エラーを返す
    if participants_data is None or len(participants_data) == 0:
        abort(500)

    # 以降、supabaseと接続ができるとみなす

    for participant in participants_data:
        participant["name"] = participant["name"].upper()

        participant["category"] = participant["Category"]["name"]
        del participant["Category"]

        participant["mode"] = (
            "team" if len(participant["ParticipantMember"]) > 0 else "single"
        )

        participant["members"] = "/".join(
            [member["name"].upper() for member in participant["ParticipantMember"]]
        )
        del participant["ParticipantMember"]

    members_data = supabase_service.get_data(
        table="ParticipantMember",
        columns=["id"],
        join_tables={
            "Participant": [
                "id",
                "year",
                "name",
                "ticket_class",
                "is_cancelled",
                "Category(name)",
                "ParticipantMember(name)",
            ],
        },
        filters={f"name__{Operator.MATCH_IGNORE_CASE}": f"%{keyword}%"},
    )

    for member in members_data:
        if member["Participant"]["year"] == year:
            participant = {
                "id": member["Participant"]["id"],
                "name": member["Participant"]["name"].upper(),
                "category": member["Participant"]["Category"]["name"],
                "ticket_class": member["Participant"]["ticket_class"],
                "is_cancelled": member["Participant"]["is_cancelled"],
                "members": "/".join(
                    [
                        m["name"].upper()
                        for m in member["Participant"]["ParticipantMember"]
                    ]
                ),
                "mode": "team",
            }
            participants_data.append(participant)

    # 重複を削除
    seen_ids = set()
    participants_data = [
        p
        for p in participants_data
        if p["id"] not in seen_ids and not seen_ids.add(p["id"])
    ]

    # 5件以上ある場合、類似度上位5チームを抽出
    if len(participants_data) > 5:
        names = [p["name"] for p in participants_data]
        top5 = process.extract(keyword, names, limit=5)
        participants_data = [participants_data[index] for _, _, index in top5]

    return jsonify(participants_data)
