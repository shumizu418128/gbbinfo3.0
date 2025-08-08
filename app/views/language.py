from urllib.parse import urlparse

from flask import redirect, request, session


def is_safe_url(target: str) -> bool:
    """
    Checks if the target URL is a safe local URL for redirection.
    """
    # Remove backslashes to prevent browser quirks
    target = target.replace("\\", "")
    parsed_url = urlparse(target)
    # Only allow relative URLs (no scheme, no netloc) and path must start with /
    return not parsed_url.scheme and not parsed_url.netloc and parsed_url.path.startswith("/")

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

    # クッキーにも保存し、referrerにリダイレクト
    session["language"] = lang_code

    if not is_safe_url(current_url):
        current_url = "/"

    return redirect(current_url)
