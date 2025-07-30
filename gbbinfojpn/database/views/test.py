"""
テスト用ビュー
Supabaseからテストデータを取得し、htmlを返す
"""

from django.http import HttpRequest
from django.shortcuts import render

from gbbinfojpn.database.models.supabase_client import supabase_service


def test_view(request: HttpRequest):
    """
    テスト用：testテーブルのデータ一覧を表示するビュー

    Supabaseのtestテーブルからデータを取得し、テンプレートに渡す。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        HttpResponse: testテーブルデータ一覧ページのレンダリング結果
    """
    # Supabaseのtestテーブルからデータを直接取得
    test_data = supabase_service.get_data(
        table="test", columns=["id", "value", "created_at"]
    )

    context = {
        "test_data": test_data,
        "title": "Testテーブルデータ一覧",
    }

    return render(request, "database/test.html", context)
