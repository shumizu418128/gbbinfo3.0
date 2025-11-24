"""
Flask アプリケーションの年度要件のテストモジュール

python -m pytest app/tests/test_year_requirements.py -v
"""

import os
import unittest

COMMON_URLS = ["/japan", "/korea", "/participants", "/rule"]


class YearRequirementsTestCase(unittest.TestCase):
    """
    年度追加時の必須要件が揃っているかを確認するテストケース

    データベースの代わりにテンプレートフォルダの内容を確認して、
    新年度追加に必要なファイルとフォルダが存在するかを検証します。
    """

    def setUp(self):
        """テストの前準備を行います。"""
        self.templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.translations_dir = os.path.join(
            os.path.dirname(__file__), "..", "translations"
        )

        # 利用可能な年度をテンプレートフォルダから取得
        self.available_years = []
        if os.path.exists(self.templates_dir):
            for item in os.listdir(self.templates_dir):
                item_path = os.path.join(self.templates_dir, item)
                if os.path.isdir(item_path) and item.isdigit():
                    self.available_years.append(int(item))
        self.available_years.sort(reverse=True)

    def test_year_template_directories_exist(self):
        """
        各年度のテンプレートディレクトリが存在することをテストします。
        """
        for year in self.available_years:
            year_dir = os.path.join(self.templates_dir, str(year))
            with self.subTest(year=year):
                self.assertTrue(
                    os.path.exists(year_dir),
                    f"年度 {year} のテンプレートディレクトリが存在しません: {year_dir}",
                )

    def test_required_template_files_exist(self):
        """
        各年度の必須テンプレートファイルが存在することをテストします（2022年は除外）。

        Returns:
            None
        """
        required_files = [
            "top.html",
            "rule.html",
            "ticket.html",
            "timetable.html",
            "top_7tosmoke.html",
        ]

        for year in self.available_years:
            if year <= 2022:
                continue  # 2022年以前は除外
            year_dir = os.path.join(self.templates_dir, str(year))
            for file_name in required_files:
                file_path = os.path.join(year_dir, file_name)
                with self.subTest(year=year, file=file_name):
                    self.assertTrue(
                        os.path.exists(file_path),
                        f"年度 {year} の必須ファイル {file_name} が存在しません: {file_path}",
                    )

    def test_world_map_directory_structure(self):
        """
        各年度のworld_mapディレクトリ構造が正しいことをテストします。
        """
        for year in self.available_years:
            year_dir = os.path.join(self.templates_dir, str(year))
            world_map_dir = os.path.join(year_dir, "world_map")

            with self.subTest(year=year):
                self.assertTrue(
                    os.path.exists(world_map_dir),
                    f"年度 {year} のworld_mapディレクトリが存在しません: {world_map_dir}",
                )
