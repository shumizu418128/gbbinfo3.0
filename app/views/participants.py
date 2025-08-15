from flask import redirect, render_template, request, session

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator
from app.util.participant_edit import team_multi_country, wildcard_rank_sort

VALID_TICKET_CLASSES = ["all", "wildcard", "seed_right"]
VALID_CANCEL = ["show", "hide", "only_cancelled"]


# MARK: 出場者ページ
def participants_view(year: int):
    """
    指定された年度の出場者ページを表示します。

    クエリパラメータに基づき、カテゴリ、チケットクラス、キャンセル状態などのフィルタを適用し、
    不正なパラメータの場合はデフォルト値でリダイレクトします。

    Args:
        request (HttpRequest): リクエストオブジェクト
        year (int): 対象年度

    Returns:
        HttpResponse: 出場者ページのテンプレートをレンダリングしたレスポンス。
                      不正なパラメータの場合はリダイレクトレスポンス。
    """
    # クエリパラメータ
    category = request.args.get("category")
    ticket_class = request.args.get("ticket_class")
    cancel = request.args.get("cancel")
    scroll = request.args.get("scroll")
    value = request.args.get("value")

    # その年のカテゴリ一覧を取得
    year_data = supabase_service.get_data(
        table="Year",
        columns=["categories"],
        filters={
            "year": year,
        },
        pandas=True,
    )
    all_categories_for_year_id = year_data["categories"].tolist()[0]

    # idから名前を取得
    category_data = supabase_service.get_data(
        table="Category",
        columns=["id", "name"],
        filters={
            f"id__{Operator.IN_}": all_categories_for_year_id,
        },
        pandas=True,
    )
    all_category_names = category_data["name"].tolist()

    # 引数の正当性チェック
    # 問題がある場合すべてデフォルト値にしてリダイレクト
    if any(
        [
            category not in all_category_names,
            ticket_class not in VALID_TICKET_CLASSES,
            cancel not in VALID_CANCEL,
        ]
    ):
        redirect_url = (
            f"/{year}/participants?category=Loopstation&ticket_class=all&cancel=show"
        )

        # スクロール・出場者検索のパラメータがある場合はそれも追加
        if scroll:
            redirect_url += f"&scroll={scroll}"
        if value:
            redirect_url += f"&value={value}"

        return redirect(redirect_url)

    # カテゴリ名からidを取得
    category_id = int(category_data[category_data["name"] == category]["id"].values[0])

    # 基本フィルター
    filters = {
        "year": year,
        "category": category_id,
    }

    # 出場権区分のフィルター
    if ticket_class == "Wildcard":
        filters[f"ticket_class__{Operator.LIKE}"] = "%Wildcard%"
    elif ticket_class == "GBB":
        filters[f"ticket_class__{Operator.NOT_LIKE}"] = "%Wildcard%"

    # 辞退者のフィルター
    if cancel == "hide":
        filters["is_cancelled"] = False
    elif cancel == "only_cancelled":
        filters["is_cancelled"] = True

    # 出場者データを取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "category", "ticket_class", "is_cancelled", "iso_code"],
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["name", "Country(names)"],
            "Country": ["iso_code", "names"],
        },
        filters=filters,
    )
    participants_data.sort(
        key=lambda x: (
            x["is_cancelled"],  # キャンセルした人は下
            x["iso_code"] == 0,  # 出場者未定枠は下
            "Wildcard" in x["ticket_class"],  # Wildcard通過者は下
            wildcard_rank_sort(x),  # Wildcardのランキング順にする
            "GBB" not in x["ticket_class"],  # GBBによるシードは上
        )
    )

    # 言語を取得
    language = session["language"]

    participants_data_edited = []

    for participant in participants_data:
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]
        participant.pop("Category")

        # 国名を取り出す
        if participant["iso_code"] == 9999:
            participant = team_multi_country(participant, language)
        else:
            participant["country"] = participant["Country"]["names"][language]
            participant.pop("Country")

        participant["is_team"] = len(participant["ParticipantMember"]) > 0

        participants_data_edited.append(participant)

    context = {
        "participants": participants_data_edited,
        "all_category": all_category_names,
        "category": category,
        "ticket_class": ticket_class,
        "cancel": cancel,
    }
    return render_template("common/participants.html", **context)


# MARK: 国別出場者ページ
def participants_country_specific_view(year: int):
    """指定された年とURLから取得した国名に基づいて、該当国の出場者リストを取得し、テンプレートにレンダリングするビュー関数。

    Args:
        year (int): 出場者データを取得する対象の年。

    Returns:
        Response: 指定国の出場者リストを含むHTMLテンプレートのレンダリング結果。

    Note:
        - URLの最後の要素から国名（例: "japan", "korea"）を取得し、該当するISOコードを割り当てる。
        - 単一国籍の出場者だけでなく、複数国籍チームの中に該当国のメンバーがいる場合もリストに含める。
        - 出場者名は大文字に変換され、カテゴリ名やチーム判定などの加工を行う。
        - 出場者リストはキャンセル状況、カテゴリ、ワイルドカード、ランキング、GBBシードの有無でソートされる。
        - レンダリングするテンプレートは国名に応じて動的に決定される（例: "common/japan.html"）。
    """
    # URLから国名を取得
    url = request.path
    country_name = url.split("/")[-1]  # 最後の要素が国名
    if country_name == "japan":
        iso_code = 392
    if country_name == "korea":
        iso_code = 410

    # 出場者データを取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "category", "ticket_class", "is_cancelled", "iso_code"],
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["name"],
        },
        filters={
            "year": year,
            "iso_code": iso_code,
        },
    )

    # 複数か国のチームも調べる
    multi_country_team_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "category", "ticket_class", "is_cancelled"],
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["name", "iso_code"],
        },
        filters={
            "year": year,
            "iso_code": 9999,
        },
    )

    # 探している国籍のチームだった場合、そのチームを追加
    for team in multi_country_team_data:
        for member in team["ParticipantMember"]:
            if member["iso_code"] == iso_code:
                participants_data.append(team)
                break

    for participant in participants_data:
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]

        participant["is_team"] = len(participant["ParticipantMember"]) > 0

    participants_data.sort(
        key=lambda x: (
            x["is_cancelled"],  # キャンセルした人は下
            x["Category"]["id"],  # カテゴリでソート
            "Wildcard" in x["ticket_class"],  # Wildcard通過者は下
            wildcard_rank_sort(x),  # Wildcardのランキング順にする
            "GBB" not in x["ticket_class"],  # GBBによるシードは上
        )
    )

    context = {
        "participants": participants_data,
    }
    return render_template(f"common/{country_name}.html", **context)
