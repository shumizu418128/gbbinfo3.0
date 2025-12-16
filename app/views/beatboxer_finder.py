from flask import abort, jsonify, request
from rapidfuzz import process

from app.models.supabase_client import supabase_service


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

    try:
        participants_data = supabase_service.get_data(
            table="Participant",
            columns=["id", "name", "category", "ticket_class", "is_cancelled"],
            order_by="category",
            join_tables={
                "Category": ["name", "is_team"],
                "ParticipantMember": ["name"],
            },
            filters={"year": year},
        )

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
                    "Category(name, is_team)",
                    "ParticipantMember(name)",
                ],
            },
            raise_error=True,
            filters={"participant!inner.year": year},
        )
    except Exception:
        abort(500)

    # 検索用に参加者名とメンバー名リスト（重複排除）をそれぞれ生成
    search_name_participants = [
        participant["name"].upper() for participant in participants_data
    ]
    search_name_members = [
        member["Participant"]["name"].upper() for member in members_data
    ]

    extract_result_participants = process.extract(
        keyword.upper(), search_name_participants, limit=5
    )
    extract_result_members = process.extract(
        keyword.upper(), search_name_members, limit=5
    )

    result = []

    for _, ratio, index in extract_result_participants:
        participant = participants_data[index]
        member_names_list = [
            member["name"].upper() for member in participant["ParticipantMember"]
        ]
        result.append(
            {
                ratio: {
                    "id": participant["id"],
                    "name": participant["name"].upper(),
                    "category": participant["Category"]["name"],
                    "ticket_class": participant["ticket_class"],
                    "members": ", ".join(member_names_list),
                    "is_cancelled": participant["is_cancelled"],
                    "mode": "single"
                    if not participant["Category"]["is_team"]
                    else "team",
                }
            }
        )

    for _, ratio, index in extract_result_members:
        member = members_data[index]
        member_names_list = [
            member["name"].upper()
            for member in member["Participant"]["ParticipantMember"]
        ]
        result.append(
            {
                ratio: {
                    "id": member["Participant"]["id"],
                    "name": member["Participant"]["name"].upper(),
                    "category": member["Participant"]["Category"]["name"],
                    "ticket_class": member["Participant"]["ticket_class"],
                    "members": ", ".join(member_names_list),
                    "is_cancelled": member["Participant"]["is_cancelled"],
                    "mode": "team",
                }
            }
        )

    result.sort(key=lambda x: list(x.keys())[0], reverse=True)
    result = [list(x.values())[0] for x in result]

    return jsonify(result)
