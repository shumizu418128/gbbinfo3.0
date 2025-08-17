from flask import redirect, render_template
from jinja2 import TemplateNotFound

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator


# MARK: ルール
def rules_view(year: int):
    """
    指定された年の大会ルールページを表示するビュー関数。

    Args:
        year (int): ルールを表示する対象の年。

    Returns:
        flask.Response: ルールページのHTMLを返す。2013年から2016年の場合はトップページにリダイレクトされる。

    Notes:
        - 2013年から2016年は非対応のため、トップページにリダイレクトされる。
        - シード権獲得者（GBBシード、その他シード、辞退者）を取得し、テンプレートに渡す。
        - ルールページのテンプレートは "{year}/rules.html" を使用する。
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
