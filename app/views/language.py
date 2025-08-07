from urllib.parse import urlparse

from flask import redirect, request, session


def change_language(BABEL_SUPPORTED_LOCALES: list[str]):
    """
    ユーザーの言語を変更し、referrerにリダイレクトするエンドポイント。

    Args:
        request (HttpRequest): リクエストオブジェクト

    Returns:
        redirect: もとのページにリダイレクト
    """
    lang_code = request.args.get("lang")

    # サポートされている言語か確認
    if lang_code not in BABEL_SUPPORTED_LOCALES:
        lang_code = "ja"

    # 直前のページ（リファラー）を取得する
    current_url = request.headers.get("Referer", "/")
    # Remove backslashes to prevent browser quirks
    current_url = current_url.replace("\\", "")
    parsed_url = urlparse(current_url)
    # Only allow relative URLs (no scheme, no netloc) and path must start with /
    if parsed_url.scheme or parsed_url.netloc or not parsed_url.path.startswith("/"):
        current_url = "/"

    # クッキーにも保存し、referrerにリダイレクト
    session["language"] = lang_code

    return redirect(current_url)
