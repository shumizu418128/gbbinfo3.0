from flask import redirect, render_template
from jinja2 import TemplateNotFound

from app.models.supabase_client import supabase_service
from app.util.filter_eq import Operator
from app.util.participant_edit import edit_country_data


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
    # 2016以前は非対応
    if year <= 2016:
        return redirect(f"/{year}/top")

    # シード権獲得者を取得
    participants_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "category", "is_cancelled", "ticket_class", "iso_code"],
        order_by="category",  # カテゴリでソート
        join_tables={
            "Category": ["id", "name", "is_team"],
            "Country": ["iso_code", "names", "iso_alpha2"],
        },
        filters={
            # Wildcardという文字列が含まれていない
            f"ticket_class__{Operator.NOT_LIKE}": "%Wildcard%",
            "year": year,
        },
    )

    # supabaseから取得失敗した場合、空のデータでページを表示する
    if not participants_data:
        context = {
            "gbb_seed": [],
            "other_seed": [],
            "cancelled": [],
        }
        return render_template(f"{year}/rule.html", **context)

    gbb_seed = []
    other_seed = []
    cancelled = []

    for participant in participants_data:
        # 全員の名前を大文字に変換
        participant["name"] = participant["name"].upper()

        # カテゴリ名を取り出す
        participant["category"] = participant["Category"]["name"]

        # メンバーがいればチームと判定
        is_team = participant["Category"]["is_team"]
        if is_team:
            participant["mode"] = "team"
        else:
            participant["mode"] = "single"

        participant.pop("Category")

        # シード権辞退者、GBBでのシード権、その他でのシード権に分類
        if participant["is_cancelled"]:
            cancelled.append(participant)
        elif "GBB" in participant["ticket_class"]:
            gbb_seed.append(participant)
        else:
            other_seed.append(participant)

        participant = edit_country_data(participant)

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
