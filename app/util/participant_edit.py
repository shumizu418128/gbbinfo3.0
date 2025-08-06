import re


def team_multi_country(team_data: dict, language: str):
    """
    チームの複数国籍をまとめる
    入力データはpandasにしないこと
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
    """出場者データの'ticket_class'が'Wildcard'の場合はランキング順の整数値を返し、それ以外は無限大を返す。

    Args:
        x (dict): 出場者データの辞書

    Returns:
        int or float: Wildcardの場合はランキング順の整数値、それ以外はfloat('inf')
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
