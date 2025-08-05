from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect


def change_language(request: HttpRequest):
    """
    ユーザーの言語を変更し、referrerにリダイレクトするエンドポイント。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        HttpResponseRedirect: リダイレクトレスポンス
    """
    lang_code = request.GET.get("lang")

    # サポートされている言語か確認
    if lang_code not in settings.SUPPORTED_LANGUAGE_CODES:
        lang_code = "ja"

    # 直前のページ（リファラー）を取得する
    current_url = request.META.get("HTTP_REFERER", "/")
    parsed_url = urlparse(current_url)

    # 内部URLかつパスが/で始まる場合のみ許可
    if parsed_url.netloc and parsed_url.netloc != request.get_host():
        current_url = "/"
    elif not parsed_url.path.startswith("/"):
        current_url = "/"

    # クッキーにも保存し、referrerにリダイレクト
    response = HttpResponseRedirect(current_url)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)

    return response
