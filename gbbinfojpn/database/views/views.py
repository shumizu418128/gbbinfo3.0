import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..models.models import DatabaseEntry, TestData, WebContent
from ..models.supabase_client import supabase_service


def web_content_list(request):
    """ウェブコンテンツ一覧を表示"""
    # DjangoのORMとSupabaseの両方からデータを取得可能
    try:
        # Supabaseから直接取得
        supabase_data = WebContent.get_published_content()

        # または通常のDjango ORM（Supabaseデータベースを使用）
        django_data = WebContent.objects.filter(published=True)

        context = {
            "supabase_content": supabase_data,
            "django_content": django_data,
        }

        return render(request, "database/content_list.html", context)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_content(request):
    """ウェブコンテンツAPI（Supabaseとの直接やり取り）"""
    if request.method == "GET":
        # コンテンツ取得
        category = request.GET.get("category")
        filters = {}
        if category:
            filters["category"] = category

        content_data = supabase_service.get_table_data("database_webcontent", **filters)
        return JsonResponse({"data": content_data})

    elif request.method == "POST":
        # コンテンツ作成
        try:
            data = json.loads(request.body)

            # Supabaseに直接挿入
            result = supabase_service.insert_data("database_webcontent", data)

            if result:
                return JsonResponse({"success": True, "data": result})
            else:
                return JsonResponse({"error": "データの保存に失敗しました"}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "無効なJSONデータです"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


def content_detail(request, content_id):
    """コンテンツ詳細（閲覧数も更新）"""
    try:
        # Django ORMでコンテンツを取得
        content = WebContent.objects.get(id=content_id)

        # 閲覧数をSupabaseで直接更新
        content.increment_view_count()

        # ORMでも更新（同期を保つため）
        content.view_count += 1
        content.save()

        context = {"content": content}
        return render(request, "database/content_detail.html", context)

    except WebContent.DoesNotExist:
        return JsonResponse({"error": "コンテンツが見つかりません"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_database_entries(request):
    """データベースエントリAPI"""
    try:
        # Supabaseから直接データを取得
        entries = DatabaseEntry.get_supabase_data()
        return JsonResponse({"data": entries})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def health_check(request):
    """システムヘルスチェック（両方のデータベース接続を確認）"""
    try:
        # SQLite接続確認（管理機能）
        from django.contrib.auth.models import User

        sqlite_ok = User.objects.exists()

        # Supabase接続確認
        supabase_ok = False
        try:
            supabase_service.get_table_data("database_databaseentry")
            supabase_ok = True
        except Exception:
            pass

        return JsonResponse(
            {
                "sqlite_connection": sqlite_ok,
                "supabase_connection": supabase_ok,
                "status": "healthy" if (sqlite_ok and supabase_ok) else "partial",
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def test_data_list(request):
    """testテーブルのデータ一覧を表示"""
    try:
        # Supabaseのtestテーブルからデータを取得
        test_data = TestData.get_test_data()
        print(test_data)

        context = {
            "test_data": test_data,
            "title": "Testテーブルデータ一覧",
        }

        return render(request, "database/test_data_list.html", context)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
