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
    referrer = request.GET.get("referrer", "/")

    # サポートされている言語か確認
    if lang_code not in settings.SUPPORTED_LANGUAGE_CODES:
        lang_code = "ja"

    # クッキーにも保存し、referrerにリダイレクト
    response = HttpResponseRedirect(referrer)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)

    return response
