import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


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


def check_locale_paths_and_languages(BABEL_SUPPORTED_LOCALES):
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

    supported_set = set(BABEL_SUPPORTED_LOCALES)

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
