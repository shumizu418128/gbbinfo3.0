from flask import redirect, render_template
from jinja2 import TemplateNotFound
from sanic.response import redirect as sanic_redirect
from sanic_ext import render

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator


# MARK: ルール（同期版）
def rules_view(year: int):
    """
    指定された年の大会ルールページを表示するビュー関数（同期版）。
    """
    # 2013-2016は非対応
    if 2013 <= year <= 2016:
        return redirect(f"/{year}/top")

    # シード権獲得者を取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "category", "is_cancelled", "ticket_class"],
        order_by="category",  # カテゴリでソート
        join_tables={
            "Category": ["id", "name"],
            "ParticipantMember": ["id"],
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

        # メンバーがいればチームと判定
        participant["is_team"] = len(participant["ParticipantMember"]) > 0

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
        return render_template(f"{year}/rule.html", **context)
    except TemplateNotFound:
        return render_template("404.html"), 404


# MARK: ルール（非同期版）
async def rules_view_async(request, year: int):
    """
    指定された年の大会ルールページを表示するビュー関数（非同期版）。
    """
    # 2013-2016は非対応
    if 2013 <= year <= 2016:
        return sanic_redirect(f"/{year}/top")

    # 暫定的に同期版を呼び出し（将来的にSupabaseを非同期化）
    # TODO: Supabaseサービスを非同期化した後、await supabase_service.get_data_async()に変更
    import asyncio
    participants_data = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase_service.get_data(
            table="Participant",
            columns=["id", "name", "category", "is_cancelled", "ticket_class"],
            order_by="category",  # カテゴリでソート
            join_tables={
                "Category": ["id", "name"],
                "ParticipantMember": ["id"],
            },
            filters={
                # Wildcardという文字列が含まれていない
                f"ticket_class__{Operator.NOT_LIKE}": "%Wildcard%",
                "year": year,
            },
        )
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

        # メンバーがいればチームと判定
        participant["is_team"] = len(participant["ParticipantMember"]) > 0

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
        return await render(f"{year}/rule.html", context=context)
    except TemplateNotFound:
        return await render("404.html", status=404)
