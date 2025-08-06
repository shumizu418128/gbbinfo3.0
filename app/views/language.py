from urllib.parse import urlparse

from flask import redirect, request, session

from app import settings


def change_language():
    """
    ユーザーの言語を変更し、referrerにリダイレクトするエンドポイント。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        redirect: もとのページにリダイレクト
    """
    lang_code = request.GET.get("lang")

    # サポートされている言語か確認
    if lang_code not in settings.BABEL_SUPPORTED_LOCALES:
        lang_code = "ja"

    # 直前のページ（リファラー）を取得する
    current_url = request.headers.get("Referer", "/")
    parsed_url = urlparse(current_url)

    # 内部URLかつパスが/で始まる場合のみ許可
    if parsed_url.netloc and parsed_url.netloc != request.host:
        current_url = "/"
    elif not parsed_url.path.startswith("/"):
        current_url = "/"

    # クッキーにも保存し、referrerにリダイレクト
    session["language"] = lang_code

    return redirect(current_url)
