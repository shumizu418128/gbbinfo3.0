from django.http import HttpRequest
from django.shortcuts import render

from ..models.supabase_client import supabase_service


def test(request: HttpRequest):
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


def participants(request: HttpRequest):
    """参加者一覧を表示"""
    # Supabaseのparticipantsテーブルからデータを直接取得
    participants_data = supabase_service.get_data(
        table="Participant", year=2025, category=1
    )

    # 国データを取得
    country_data = supabase_service.get_data(
        table="Country", columns=["names", "iso_code"]
    )

    # 日本語の国名を取得
    ja_country_data = {}
    for data in country_data:
        if data["iso_code"] != 0:
            ja_name = data["names"]["ja"]
            iso_code = data["iso_code"]
            ja_country_data[iso_code] = ja_name

    # 参加者データの国名を日本語に変換
    for participant in participants_data:
        iso_code = participant["iso_code"]
        participant["country"] = ja_country_data[iso_code]

        # 無い場合はエラー
        if participant["country"] == "":
            raise ValueError(f"国名が見つかりません: {participant['iso_code']}")

    context = {
        "participants_data": participants_data,
        "title": "参加者一覧",
    }

    return render(request, "database/participants.html", context)
