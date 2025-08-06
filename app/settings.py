import os
import re
from datetime import datetime
from pathlib import Path

from util.filter_eq import Operator

from app.models.supabase_client import supabase_service

BASE_DIR = Path(__file__).resolve().parent

LANGUAGES = [
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fr", "Français"),
    ("hi", "हिन्दी"),
    ("hu", "Magyar"),
    ("it", "Italiano"),
    ("ms", "Bahasa MY"),
    ("no", "Norsk"),
    ("ta", "தமிழ்"),
    ("th", "ไทย"),
    ("zh-hans", "简体中文"),
    ("zh-hant", "繁體中文"),
]
BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    BABEL_DEFAULT_LOCALE = "ja"
    BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]
    CACHE_TYPE = "filesystem"
    CACHE_DIR = "cache-directory"
    CACHE_DEFAULT_TIMEOUT = 0
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False


class TestConfig(Config):
    CACHE_TYPE = "null"
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SECRET_KEY = "test"


LAST_UPDATED = "UPDATE " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " JST"


def get_translated_urls():
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

    po_file_path = BASE_DIR / "locale" / language / "LC_MESSAGES" / "django.po"
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


def delete_world_map():
    templates_dir = os.path.join(BASE_DIR, "app", "templates")
    if os.path.exists(templates_dir):
        for year_dir in os.listdir(templates_dir):
            year_path = os.path.join(templates_dir, year_dir)
            if os.path.isdir(year_path):
                world_map_path = os.path.join(year_path, "world_map")
                if os.path.exists(world_map_path):
                    for file in os.listdir(world_map_path):
                        if file.endswith(".html"):
                            file_path = os.path.join(world_map_path, file)
                            os.remove(file_path)


def check_locale_paths_and_languages():
    """
    LOCALE_PATHS内の各フォルダ（言語コード）とSUPPORTED_LANGUAGE_CODESが一致しているかを検証します。
    ただし、日本語（'ja'）は例外としてチェック対象外とします。
    zh-hansとzh_Hans、zh-hantとzh_Hantは同じものとして扱います。
    一致しない場合は例外を発生させます。

    Raises:
        Exception: サポートされていない言語コードのlocaleフォルダが存在する場合、または
                  SUPPORTED_LANGUAGE_CODESに存在するがlocaleフォルダがない場合。
                  （いずれも日本語は例外）
    """
    # LOCALE_PATHSからlocaleディレクトリのパスを取得
    locale_path = BASE_DIR / "locale"

    # localeディレクトリ内の言語コードフォルダを取得
    locale_dirs_set = set()
    for language_folder in os.listdir(locale_path):
        item_path = os.path.join(locale_path, language_folder)
        if os.path.isdir(item_path):
            locale_dirs_set.add(language_folder)

    supported_set = set([code for code, _ in LANGUAGES])

    # 中国語の正規化関数
    def normalize_chinese_code(code):
        if code in ["zh-hans", "zh_Hans"]:
            return "zh-hans"
        elif code in ["zh-hant", "zh_Hant"]:
            return "zh-hant"
        return code

    # 正規化したセットを作成
    locale_dirs_normalized = {normalize_chinese_code(code) for code in locale_dirs_set}
    supported_normalized = {normalize_chinese_code(code) for code in supported_set}

    # 日本語（'ja'）は例外として除外
    locale_dirs_normalized_no_ja = locale_dirs_normalized - {"ja"}
    supported_normalized_no_ja = supported_normalized - {"ja"}

    # localeディレクトリにあるが、SUPPORTED_LANGUAGE_CODESにないもの
    extra_locales = locale_dirs_normalized_no_ja - supported_normalized_no_ja
    # SUPPORTED_LANGUAGE_CODESにあるが、localeディレクトリにないもの
    missing_locales = supported_normalized_no_ja - locale_dirs_normalized_no_ja

    error_msgs = []
    if extra_locales:
        error_msgs.append(
            f"LOCALE_PATHSに存在するがSUPPORTED_LANGUAGE_CODESに含まれていない言語コード: {sorted(extra_locales)}"
        )
    if missing_locales:
        error_msgs.append(
            f"SUPPORTED_LANGUAGE_CODESに存在するがLOCALE_PATHSにフォルダが存在しない言語コード: {sorted(missing_locales)}"
        )
    if error_msgs:
        raise Exception("ロケール設定エラー:\n" + "\n".join(error_msgs))


TRANSLATED_URLS = get_translated_urls()
delete_world_map()
check_locale_paths_and_languages()
