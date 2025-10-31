import re

from app.config.config import (
    ISO_CODE_COUNTRY_ISO_ALPHA2_NOT_FOUND,
    ISO_CODE_COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND,
    ISO_CODE_NOT_FOUND,
    MULTI_COUNTRY_TEAM_ISO_CODE,
)


def edit_country_data(beatboxer_data: dict, language: str = ""):
    """
    ISOコードに基づいてビートボクサーデータの辞書に国情報を追加して編集します。

    Args:
        beatboxer_data (dict): ビートボクサーまたはチームのデータを含む辞書。'iso_code' または 'Participant' に 'iso_code' を含む必要があります。複数国籍のチームの場合は、メンバーの国を含む 'ParticipantMember' が必要です。
        language (str, optional): 国名の言語コード（例: 'ja', 'en'）。空の場合、ISO alpha2コードのみが処理されます。

    Returns:
        dict: 修正されたbeatboxer_data。'country'（言語が指定されている場合）と'iso_alpha2'キーが追加され、'Country'キーが削除されます。

    Raises:
        ValueError: beatboxer_dataがdictでない場合、ISOコードが見つからない場合、または国データが見つからない場合に発生します。

    Note:
        単一国籍のエントリの場合、'Country.names[language]' から 'country' を設定し、'iso_alpha2' をリストとして設定します。
        複数国籍のチーム（iso_code == MULTI_COUNTRY_TEAM_ISO_CODE）の場合、メンバーの国名とISO alpha2を集約します。
        'Country' は 'names' 辞書と 'iso_alpha2' キーを持つと仮定します。
    """
    if not isinstance(beatboxer_data, dict):
        raise ValueError("beatboxer_dataはdictである必要があります")

    # iso_codeを取得（0とNoneを区別するため、明示的にis Noneでチェック）
    iso_code = beatboxer_data.get("iso_code")
    if iso_code is None:
        iso_code = beatboxer_data.get("Participant", {}).get("iso_code")
    if iso_code is None:
        iso_code = beatboxer_data.get("Country", {}).get("iso_code")

    # 出場者未定
    if iso_code == 0:
        beatboxer_data["iso_alpha2"] = []
        beatboxer_data["country"] = "-"
        return beatboxer_data

    # iso_code取得失敗
    if iso_code is None:
        raise ValueError(ISO_CODE_NOT_FOUND)

    # 1国籍のチームの場合、国名を取得して終了
    if iso_code != MULTI_COUNTRY_TEAM_ISO_CODE:
        try:
            if language:
                beatboxer_data["country"] = beatboxer_data["Country"]["names"][language]
            beatboxer_data["iso_alpha2"] = [beatboxer_data["Country"]["iso_alpha2"]]
            beatboxer_data.pop("Country")
        except KeyError as err:
            if language:
                raise ValueError(ISO_CODE_COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND) from err
            raise ValueError(ISO_CODE_COUNTRY_ISO_ALPHA2_NOT_FOUND) from err
        return beatboxer_data

    # 複数国籍のチームの場合、全メンバーの国名を取得
    # 辞書を使用してISO alpha2をキーとし、国名とのペアを維持(重複も自動除去)
    country_dict = {}
    members = beatboxer_data["ParticipantMember"]

    for member in members:
        try:
            iso_alpha2 = member["Country"]["iso_alpha2"]
            if language:
                country_name = member["Country"]["names"][language]
                country_dict[iso_alpha2] = country_name
            else:
                country_dict[iso_alpha2] = None
        except KeyError:
            if language:
                raise ValueError(ISO_CODE_COUNTRY_NAMES_OR_ALPHA2_NOT_FOUND)
            raise ValueError(ISO_CODE_COUNTRY_ISO_ALPHA2_NOT_FOUND)

    if language:
        beatboxer_data["country"] = " / ".join(country_dict.values())
    beatboxer_data["iso_alpha2"] = list(country_dict.keys())
    beatboxer_data.pop("Country")

    return beatboxer_data


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

    return (float("inf"), float("inf"))
