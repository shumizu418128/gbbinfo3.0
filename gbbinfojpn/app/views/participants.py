from django.http import HttpRequest
from django.shortcuts import redirect, render

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.common.filter_eq import Operator

VALID_TICKET_CLASSES = ["all", "wildcard", "seed_right"]
VALID_CANCEL = ["show", "hide", "only_cancelled"]


def wildcard_rank_sort(x):
    """出場者データの'ticket_class'が'Wildcard'の場合はランキング順の整数値を返し、それ以外は無限大を返す。

    Args:
        x (dict): 出場者データの辞書

    Returns:
        int or float: Wildcardの場合はランキング順の整数値、それ以外はfloat('inf')
    """
    if "Wildcard" in x["ticket_class"]:
        return int(x["ticket_class"].replace("Wildcard ", ""))
    else:
        return float("inf")


def participants_view(request: HttpRequest, year: int):
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
    category = request.GET.get("category")
    ticket_class = request.GET.get("ticket_class")
    cancel = request.GET.get("cancel")
    scroll = request.GET.get("scroll")
    value = request.GET.get("value")

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
        columns=["name", "category", "ticket_class", "is_cancelled", "iso_code"],
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["participant", "name"],
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
    language = request.LANGUAGE_CODE

    for participant in participants_data:
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]
        participant.pop("Category")

        # メンバー名を取り出す
        participant["members"] = ", ".join(
            member["name"].upper() for member in participant["ParticipantMember"]
        )
        participant.pop("ParticipantMember")

        # 国名を取り出す
        participant["country"] = participant["Country"]["names"][language]
        participant.pop("Country")

    context = {
        "participants": participants_data,
        "all_category": all_category_names,
        "category": category,
        "ticket_class": ticket_class,
        "cancel": cancel,
    }
    return render(request, "common/participants.html", context)
