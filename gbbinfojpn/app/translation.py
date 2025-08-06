import re

from django.conf import settings

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.common.filter_eq import Operator


def _get_translated_urls():
    r"""
    英語（en）のdjango.poファイルから、翻訳済みページのURLパス一覧を取得する内部関数。

    Returns:
        set: 翻訳が存在するページのURLパスのセット

    Note:
        django.poのmsgidコメント（例: #: .\gbbinfojpn\app\templates\2024\rule.html:3）から
        テンプレートパスを抽出し、URLパスに変換します。
        common/配下のテンプレートは年度ごとに展開されるため、全年度分を生成します。
        base.html, includes, 404.html等は除外します。
    """
    language = "en"
    po_file_path = f"{settings.LOCALE_PATHS[0]}/{language}/LC_MESSAGES/django.po"
    translated_urls = set()

    try:
        with open(po_file_path, "r", encoding="utf-8") as f:
            po_content = f.read()
    except FileNotFoundError:
        return set()

    exclude_patterns = [
        r"\\includes\\",  # includesディレクトリ
        r"base\.html",  # base.html
        r"404\.html",  # 404.html
    ]

    for line in po_content.split("\n"):
        if line.startswith("#: .\\gbbinfojpn\\app\\templates\\"):
            # コメント行から複数パスを取得
            paths = line.replace("#:", "").split()
            for path in paths:
                # 除外条件
                if any(re.search(pattern, path) for pattern in exclude_patterns):
                    continue

                # パスからテンプレート部分を抽出
                m = re.match(r"\.\\gbbinfojpn\\app\\templates\\(.+?\.html)", path)
                if not m:
                    continue
                template_path = m.group(1)

                # 年度ディレクトリ or commonディレクトリ
                if template_path.startswith("common\\"):
                    # 年度ごとに展開
                    year_data = supabase_service.get_data(
                        table="Year",
                        columns=["year"],
                        filters={f"categories__{Operator.IS_NOT}": None},
                        pandas=True,
                    )
                    available_years = year_data["year"].tolist()
                    for year in available_years:
                        # common\foo.html → /{year}/foo
                        url_path = (
                            "/"
                            + str(year)
                            + "/"
                            + template_path.replace("common\\", "").replace(".html", "")
                        )
                        translated_urls.add(url_path)
                else:
                    # 2024\foo.html → /2024/foo
                    url_path = "/" + template_path.replace("\\", "/").replace(
                        ".html", ""
                    )
                    translated_urls.add(url_path)

    return translated_urls


# 定数として翻訳されたURLを定義
TRANSLATED_URLS = None


def initialize_translated_urls():
    """
    翻訳されたURLの定数を初期化します（アプリ起動時に呼び出される）。

    Note:
        _get_translated_urls() 関数を呼び出し、翻訳済みページのURLパス一覧を取得します。
        取得したURLパス一覧を TRANSLATED_URLS 定数に格納します。

    Returns:
        None
    """
    global TRANSLATED_URLS
    TRANSLATED_URLS = _get_translated_urls()
