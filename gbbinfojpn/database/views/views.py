from django.shortcuts import render

from ..models.supabase_client import supabase_service


def test(request):
    """testテーブルのデータ一覧を表示

    シンプルなビューでSupabaseから直接データを取得して表示します。
    TestDataについては表をそのまま出すだけの実装です。
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
