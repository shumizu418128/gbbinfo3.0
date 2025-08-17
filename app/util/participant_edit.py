import re


def team_multi_country(team_data: dict, language: str):
    """
    チームデータから全メンバーの国名を取得し、指定言語で結合した新しい辞書を返す関数。

    Args:
        team_data (dict): チーム情報を含む辞書。'ParticipantMember'キーにメンバーリストが含まれ、各メンバーは'Country'（'names'辞書を含む）を持つ必要がある。
        language (str): 国名を取得する言語コード（例: 'ja', 'en' など）。

    Returns:
        dict: 元のチームデータに'member'全員の国名を指定言語で結合した'country'キーを追加し、'Country'キーを除去した新しい辞書。

    Raises:
        ValueError: team_dataがdictでない場合、またはメンバーの'Country'情報が不足している場合に発生。

    Note:
        'ParticipantMember'の各要素は、'Country'キーを持ち、その中に'names'辞書（言語コードをキー、国名を値とする）が含まれている必要があります。
        例:
        team_data = {
            "ParticipantMember": [
                {"Country": {"names": {"ja": "日本", "en": "Japan"}}},
                {"Country": {"names": {"ja": "フランス", "en": "France"}}}
            ],
            ...
        }
    """
    if type(team_data) is not dict:
        raise ValueError("beatboxer_dataはdictである必要があります")

    combined_data = team_data.copy()

    # 全メンバーの国名を取得
    country_list = set()
    members = team_data["ParticipantMember"]

    for member in members:
        try:
            country_list.add(member["Country"]["names"][language])
        except KeyError:
            raise ValueError(
                "ParticipantMemberにCountryが存在しません Participantテーブルを取得する際に、Country(names)をjoinさせてください"
            )

    combined_data["country"] = " / ".join(sorted(country_list))
    combined_data.pop("Country")

    return combined_data


def wildcard_rank_sort(x):
    """
    ワイルドカードの順位でソートするためのキーを返す関数

    Args:
        x (dict): 'ticket_class'キーを含む辞書。例: {'ticket_class': 'Wildcard 1 (2020)'}。

    Returns:
        tuple: (year, rank) のタプル。'ticket_class'がワイルドカードでない場合は (float("inf"), float("inf")) を返す。

    Note:
        'ticket_class'が "Wildcard 1 (2020)" または "Wildcard 1" の形式であることを想定。
    """
    if "Wildcard" in x["ticket_class"]:
        # 例: "Wildcard 1 (2020)" または "Wildcard 1" の両方に対応
        m = re.match(r"Wildcard\s+(\d+)(?:\s*\((\d{4})\))?", x["ticket_class"])
        if m:
            rank = int(m.group(1))
            year = int(m.group(2)) if m.group(2) else 0  # 年が無い場合は0
            return (year, rank)
        else:
            return (float("inf"), float("inf"))
    else:
        return (float("inf"), float("inf"))
