import os

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


@require_GET
@cache_control(max_age=3600)  # 1時間キャッシュ
def serve_static_file(request, file_path):
    """
    静的ファイルを提供するビュー
    """
    # セキュリティ: パストラバーサル攻撃を防ぐ
    if ".." in file_path or file_path.startswith("/"):
        raise Http404()

    # ファイルパスを構築
    static_dir = os.path.join(settings.BASE_DIR, "gbbinfojpn", "app", "static")
    full_path = os.path.join(static_dir, file_path)

    # ファイルが存在するかチェック
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404()

    # ファイルがstaticディレクトリ内にあることを確認（セキュリティ）
    if not os.path.commonpath([static_dir, full_path]).startswith(static_dir):
        raise Http404()

    # ファイルタイプに基づいてContent-Typeを設定
    content_type = get_content_type(file_path)

    try:
        with open(full_path, "rb") as f:
            content = f.read()
        return HttpResponse(content, content_type=content_type)
    except IOError:
        raise Http404()


def get_content_type(file_path):
    """
    ファイル拡張子に基づいてContent-Typeを返す
    """
    extension = os.path.splitext(file_path)[1].lower()

    content_types = {
        ".txt": "text/plain; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".xml": "application/xml; charset=utf-8",
        ".ico": "image/x-icon",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".htm": "text/html; charset=utf-8",
    }

    return content_types.get(extension, "application/octet-stream")


@require_GET
@cache_control()
def ads_txt(request):
    """
    ads.txtファイルを提供する専用ビュー
    """
    return serve_static_file(request, "ads.txt")


@require_GET
@cache_control()
def manifest_json(request):
    """
    manifest.jsonファイルを提供する専用ビュー
    """
    return serve_static_file(request, "manifest.json")


@require_GET
@cache_control()
def robots_txt(request):
    """
    robots.txtファイルを提供する専用ビュー
    """
    return serve_static_file(request, "robots.txt")


@require_GET
@cache_control()
def favicon_ico(request):
    """
    favicon.icoファイルを提供する専用ビュー
    """
    return serve_static_file(request, "favicon.ico")


@require_GET
@cache_control()
def service_worker_js(request):
    """
    service-worker.jsファイルを提供する専用ビュー
    """
    return serve_static_file(request, "service-worker.js")


@require_GET
@cache_control()
def apple_touch_icon(request):
    """
    apple-touch-icon.pngファイルを提供する専用ビュー
    """
    return serve_static_file(request, "icon_512.png")


@require_GET
@cache_control()
def discord(request):
    """
    discordファイルを提供する専用ビュー
    """
    return serve_static_file(request, "discord")
