"""
Sitemaps for gbbinfojpn app.

Google スタイルの docstring を使用してサイトマップクラスを定義します。
"""

import os

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from gbbinfojpn.app.views.common import get_available_years


class StaticViewSitemap(Sitemap):
    """静的なビュー用のサイトマップクラス.

    各年のコンテンツや固定ページのURLを動的に生成します。
    """

    priority = 0.8
    changefreq = "weekly"

    def items(self):
        """サイトマップに含めるURLパターンのリストを返します.

        各年度ディレクトリとothersディレクトリ内のHTMLファイルを動的に検索し、
        実際に存在するファイルのみをサイトマップに含めます。

        Returns:
            list: URL名とパラメータのタプルのリスト
        """
        items = []

        # テンプレートディレクトリのパス
        template_dir = os.path.join(settings.BASE_DIR, "gbbinfojpn", "app", "templates")

        # 年別のコンテンツ
        years = get_available_years()

        for year in years:
            year_dir = os.path.join(template_dir, str(year))
            if os.path.exists(year_dir):
                # 年度ディレクトリ内の全HTMLファイルを動的に取得
                html_files = [
                    f
                    for f in os.listdir(year_dir)
                    if f.endswith(".html") and os.path.isfile(os.path.join(year_dir, f))
                ]

                for html_file in html_files:
                    # ファイル名から拡張子を除去してcontent名を取得
                    content_name = html_file.replace(".html", "")
                    items.append(
                        ("app:common", {"year": year, "content": content_name})
                    )

                # participantsとresultページ（これらは動的に生成される）
                items.append(("app:participants", {"year": year}))
                items.append(("app:japan", {"year": year}))
                items.append(("app:korea", {"year": year}))

                # 国別ページ（2017年以降）
                if year >= 2017:
                    items.append(("app:result", {"year": year}))

        # その他の固定ページ
        others_dir = os.path.join(template_dir, "others")
        if os.path.exists(others_dir):
            # othersディレクトリ内の全HTMLファイルを動的に取得
            other_html_files = [
                f
                for f in os.listdir(others_dir)
                if f.endswith(".html") and os.path.isfile(os.path.join(others_dir, f))
            ]

            for html_file in other_html_files:
                # ファイル名から拡張子を除去してcontent名を取得
                content_name = html_file.replace(".html", "")
                items.append(("app:others", {"content": content_name}))

        return items

    def location(self, item):
        """各アイテムのURLを生成します.

        Args:
            item: URL名とパラメータのタプル

        Returns:
            str: 生成されたURL
        """
        url_name, kwargs = item
        return reverse(url_name, kwargs=kwargs)

    def lastmod(self, item):
        """最終更新日を返します.

        Args:
            item: URL名とパラメータのタプル

        Returns:
            None: 現在は最終更新日を追跡していないためNoneを返す
        """
        return None
