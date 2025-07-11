import json

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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


@csrf_exempt  # TODO: 本番環境では削除する HTMLには{% csrf_token %}を記載する
@require_POST  # POSTリクエストのみ受け付ける
def test_add_country(request: HttpRequest):
    """countryテーブルに国名を追加

    iso_code (int): ISO国コード。主キーとして設定されます。
    latitude (Decimal, optional): 緯度。最大8桁、小数点以下6桁。
    longitude (Decimal, optional): 経度。最大9桁、小数点以下6桁。
    names (JSONField): 多言語名称を格納するJSONフィールド。
        {'en': 'Japan', 'ja': '日本', ...} の形式で保存されます。
    created_at (DateTimeField): レコード作成日時。自動設定されます。
    updated_at (DateTimeField): レコード更新日時。自動更新されます。

    """
    try:
        data = json.loads(request.body)
        iso_code = data.get("iso_code")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        names = data.get("names")
    except Exception as e:
        return JsonResponse({"error": f"リクエストデータの解析に失敗しました: {str(e)}"}, status=400)

    supabase_service.insert_data(
        table_name="Country",
        data={
            "iso_code": iso_code,
            "latitude": latitude,
            "longitude": longitude,
            "names": names,
        },
    )
    return JsonResponse({"message": "国情報が追加されました。"})
