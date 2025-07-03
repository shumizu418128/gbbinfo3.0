from django.http import JsonResponse
from django.shortcuts import render

from ..models.models import TestData


def test(request):
    """testテーブルのデータ一覧を表示"""
    try:
        # Supabaseのtestテーブルからデータを取得
        test_data = TestData.get_all_data()

        context = {
            "test_data": test_data,
            "title": "Testテーブルデータ一覧",
        }

        return render(request, "database/test.html", context)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
