import re

from django.conf import settings
from django.core.cache import cache

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.common.filter_eq import Operator


def _cache_translated_urls():
    """
    翻訳が存在するページのパス一覧をキャッシュします
    """
    language = "en"

    po_file_path = f"{settings.LOCALE_PATHS[0]}/{language}/LC_MESSAGES/messages.po"

    # キャッシュにない場合は読み込み
    translated_urls = set()

    try:
        with open(po_file_path, "r", encoding="utf-8") as f:
            po_content = f.read()
    except FileNotFoundError:
        return

    exclude_words = [r":\d+", "templates/", ".html"]

    for line in po_content.split("\n"):
        if line.startswith("#: templates/"):
            paths = line.replace("#:", "").split()

            for path in paths:
                # 除外条件
                if any(
                    exclude in path
                    for exclude in [
                        "templates/base.html",
                        "templates/includes/",
                        "404.html",
                    ]
                ):
                    continue

                # パスの正規化
                if path.startswith("templates/"):
                    for word in exclude_words:
                        path = re.sub(word, "", path)

                # common/の場合は年度を追加
                if path.startswith("common/"):
                    year_data = supabase_service.get_data(
                        table="Year",
                        columns=["year"],
                        filters={f"categories__{Operator.IS_NOT}": None},
                    )
                    available_years = [item["year"] for item in year_data]
                    for year in available_years:
                        formatted_path = f"/{year}/{path.replace('common/', '')}"
                        translated_urls.add(formatted_path)
                    continue

                translated_urls.add("/" + path)

    cache.set(f"translated_urls_{language}", translated_urls)

