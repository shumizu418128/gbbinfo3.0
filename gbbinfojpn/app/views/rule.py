from django.http import HttpRequest
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from gbbinfojpn.app.views import common
from gbbinfojpn.common.filter_eq import Operator
from gbbinfojpn.app.models.supabase_client import supabase_service


def rules_view(request: HttpRequest, year: int):
    # シード権獲得者を取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["name", "category", "is_cancelled", "ticket_class"],
        order_by="category",  # カテゴリでソート
        join_tables={
            "Category": ["id", "name"],
        },
        filters={
            # Wildcardという文字列が含まれていない
            f"ticket_class__{Operator.NOT_LIKE}": "%Wildcard%",
            "year": year,
        },
    )

    gbb_seed = []
    other_seed = []
    cancelled = []

    for participant in participants_data:
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]
        participant.pop("Category")

        # シード権辞退者、GBBでのシード権、その他でのシード権に分類
        if participant["is_cancelled"]:
            cancelled.append(participant)
        elif "GBB" in participant["ticket_class"]:
            gbb_seed.append(participant)
        else:
            other_seed.append(participant)

    # シード権獲得者を表示
    context = {
        "gbb_seed": gbb_seed,
        "other_seed": other_seed,
        "cancelled": cancelled,
    }
    try:
        return render(request, f"{year}/rule.html", context)
    except TemplateDoesNotExist:
        return common.not_found_page_view(request)
