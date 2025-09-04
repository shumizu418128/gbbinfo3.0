from urllib.parse import urlparse

from flask import redirect, request, session
from sanic.response import redirect as sanic_redirect


# MARK: URL結合
def build_path_with_query_and_fragment(parsed):
    """URLのパス、クエリ、フラグメントを結合して返す。

    Args:
        parsed (ParseResult): 解析済みのURL。

    Returns:
        str: パス、クエリ、フラグメントを結合したURL。
    """
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    if parsed.fragment:
        path = f"{path}#{parsed.fragment}"
    return path


def is_same_origin(parsed, host):
    return parsed.scheme in ("http", "https") and parsed.netloc == host


def is_same_origin_async(parsed, request):
    return parsed.scheme in ("http", "https") and parsed.netloc == request.host


# MARK: 言語変更（同期版）
def change_language(BABEL_SUPPORTED_LOCALES: list[str]):
    """言語を変更し、安全に元のページへリダイレクトする（同期版）。

    Args:
        BABEL_SUPPORTED_LOCALES (list[str]): サポートする言語コードの一覧。

    Returns:
        Response: 安全と判断したリファラー（またはルート）へのリダイレクト。
    """
    lang_code = request.args.get("lang")

    # サポートされている言語か確認
    if lang_code not in BABEL_SUPPORTED_LOCALES:
        lang_code = "ja"

    # 直前のページ（リファラー）を取得する
    referrer = request.headers.get("Referer")

    # リダイレクト先の決定（安全性を優先）
    next_url = "/"
    if referrer:
        parsed = urlparse(referrer)
        # 相対URL（同一オリジン相対パス）を許可
        if not parsed.scheme and not parsed.netloc:
            # 先頭が"/"でない場合は安全のためルートへ
            if (parsed.path or "").startswith("/"):
                next_url = build_path_with_query_and_fragment(parsed)
        # 同一オリジンの絶対URLを許可
        elif is_same_origin(parsed, request.host):
            next_url = build_path_with_query_and_fragment(parsed)

    # 言語をセッションに保存
    session["language"] = lang_code

    return redirect(next_url)


# MARK: 言語変更（非同期版）
async def change_language_async(request):
    """言語を変更し、安全に元のページへリダイレクトする（非同期版）。

    Args:
        request: Sanicリクエストオブジェクト

    Returns:
        Response: 安全と判断したリファラー（またはルート）へのリダイレクト。
    """
    # サポートされている言語コードを取得（main.pyからインポートする必要を避けるため、ハードコード）
    BABEL_SUPPORTED_LOCALES = [
        "ja", "ko", "en", "de", "es", "fr", "hi", "hu", "it", "ms", "no", "pt", "ta", "th", "zh_Hans_CN", "zh_Hant_TW"
    ]

    lang_code = request.args.get("lang")

    # サポートされている言語か確認
    if lang_code not in BABEL_SUPPORTED_LOCALES:
        lang_code = "ja"

    # 直前のページ（リファラー）を取得する
    referrer = request.headers.get("Referer")

    # リダイレクト先の決定（安全性を優先）
    next_url = "/"
    if referrer:
        parsed = urlparse(referrer)
        # 相対URL（同一オリジン相対パス）を許可
        if not parsed.scheme and not parsed.netloc:
            # 先頭が"/"でない場合は安全のためルートへ
            if (parsed.path or "").startswith("/"):
                next_url = build_path_with_query_and_fragment(parsed)
        # 同一オリジンの絶対URLを許可
        elif is_same_origin_async(parsed, request):
            next_url = build_path_with_query_and_fragment(parsed)

    # 言語をセッション（またはcookie）に保存
    # Sanicではrequest.ctx.sessionまたはcookieを使用
    response = sanic_redirect(next_url)
    response.cookies["language"] = lang_code
    response.cookies["language"]["max-age"] = 365 * 24 * 60 * 60  # 1年間有効

    return response
