import os
from time import sleep

import polib
from google import genai
from pydantic import BaseModel
from tqdm import tqdm

from app.config.logging_config import get_logger

logger = get_logger(__name__)

BASE_DIR = os.path.abspath("app")
LOCALE_DIR = os.path.join(BASE_DIR, "translations")
POT_FILE = os.path.join(BASE_DIR, "messages.pot")
CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")
BABEL_SUPPORTED_LOCALES = [
    "ko",
    "en",
    "de",
    "es",
    "fr",
    "hi",
    "hu",
    "it",
    "ms",
    "no",
    "pt",
    "ta",
    "th",
    "zh_Hans_CN",
    "zh_Hant_TW",
]


GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_SLEEP_TIME = 4


class Translation(BaseModel):
    translation: str


def gemini_translate(text, lang):
    client = genai.Client()
    prompt = f"""Translate the following text to language code:'{lang}'.
Important instructions:
1. Return ONLY the translated text
2. Do NOT add any placeholders or variables that weren't in the original text
3. Do NOT translate any text that looks like {{variable_name}} - keep it exactly as is
4. Do NOT add any explanatory text or notes

Text to translate: {text}"""

    while True:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Translation,
                },
            )
            break
        except Exception as e:
            if e.error.code == 503:
                sleep(GEMINI_SLEEP_TIME)
                continue
            raise

    return response.parsed.translation


def reuse_obsolete_translations(po):
    """
    コメントアウトされた翻訳（obsolete entries）を再利用する。

    Args:
        po: polib.POFile オブジェクト
    """
    # コメントアウトされたエントリを取得
    obsolete_entries = po.obsolete_entries()

    if not obsolete_entries:
        return

    logger.info(
        f"[reuse_obsolete_translations] Found {len(obsolete_entries)} obsolete translations to check for reuse"
    )

    # 現在のエントリの辞書を作成（msgid -> entry）
    current_entries = {entry.msgid: entry for entry in po}

    reused_count = 0

    for obsolete_entry in obsolete_entries:
        # コメントアウトされた翻訳に有効なmsgstrがある場合
        if obsolete_entry.msgstr and obsolete_entry.msgstr.strip():
            # 同じmsgidの現在のエントリが存在し、未翻訳またはfuzzyの場合
            if obsolete_entry.msgid in current_entries:
                current_entry = current_entries[obsolete_entry.msgid]

                # 未翻訳またはfuzzyの場合のみ再利用
                if (
                    not current_entry.msgstr
                    or current_entry.msgstr.strip() == ""
                    or "fuzzy" in current_entry.flags
                ):
                    # 翻訳を再利用
                    current_entry.msgstr = obsolete_entry.msgstr

                    # fuzzyフラグを削除
                    if "fuzzy" in current_entry.flags:
                        current_entry.flags.remove("fuzzy")

                    # コメントに再利用の情報を追加
                    if not current_entry.comment:
                        current_entry.comment = ""
                    current_entry.comment += "\nReused from obsolete translation"

                    reused_count += 1
                    logger.debug(
                        f"[reuse_obsolete_translations] Reused translation for: {obsolete_entry.msgid[:50]}..."
                    )

    logger.info(
        f"[reuse_obsolete_translations] Reused {reused_count} translations from obsolete entries"
    )


def prioritize_existing_translations(po, untranslated_entries):
    """
    既存の翻訳を優先的に使用する。
    同じmsgidの翻訳が既に存在する場合、それを優先的に使用する。

    Args:
        po: polib.POFile オブジェクト
        untranslated_entries: 未翻訳エントリのリスト
    """
    # 全てのエントリの辞書を作成（msgid -> entry）
    # all_entries = {entry.msgid: entry for entry in po}

    prioritized_count = 0

    for entry in untranslated_entries[
        :
    ]:  # コピーを作成してイテレーション中にリストを変更
        # 同じmsgidの他のエントリを検索
        for other_entry in po:
            if (
                other_entry.msgid == entry.msgid
                and other_entry != entry
                and other_entry.msgstr
                and other_entry.msgstr.strip()
            ):
                # 既存の翻訳をコピー
                entry.msgstr = other_entry.msgstr

                # fuzzyフラグを削除
                if "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")

                # コメントに優先使用の情報を追加
                if not entry.comment:
                    entry.comment = ""
                entry.comment += "\nReused from existing translation"

                # 未翻訳リストから削除
                untranslated_entries.remove(entry)
                prioritized_count += 1
                logger.debug(
                    f"[prioritize_existing_translations] Prioritized existing translation for: {entry.msgid[:50]}..."
                )
                break

    logger.info(
        f"[prioritize_existing_translations] Prioritized {prioritized_count} existing translations"
    )


def translate(path, lang):
    try:
        logger.info(f"[main] Processing {lang}: {path}")
        po = polib.pofile(path)
    except Exception as e:
        logger.exception(f"[main] Error reading {path}: {e}")
        raise

    ZH = ["zh_Hans_CN", "zh_Hant_TW"]

    # コメントアウトされた翻訳を再利用
    reuse_obsolete_translations(po)

    # エスケープが異常に多い場合は fuzzy フラグを付与
    for entry in po.translated_entries():
        if "\\" in entry.msgstr:
            entry.flags.append("fuzzy")
        if entry.msgid == entry.msgstr:  # 同じ言葉で
            if lang not in ZH:  # 中国語ではない場合はフラグを付与
                entry.flags.append("fuzzy")
            elif len(entry.msgid) > 10:  # 中国語でも、10文字以上は fuzzy フラグを付与
                entry.flags.append("fuzzy")

    po.save(path)  # プレースホルダーの検証結果を保存
    po = polib.pofile(path)  # 再度ファイルを読み込む

    # 翻訳が必要なエントリを処理
    untranslated_entries = po.untranslated_entries() + po.fuzzy_entries()
    msgids = [entry.msgid for entry in untranslated_entries]
    if msgids:
        logger.debug(f"[main] Message IDs to translate: {msgids}")

    # 既存の翻訳を優先的に使用
    prioritize_existing_translations(po, untranslated_entries)

    for entry in tqdm(untranslated_entries, desc=f"{lang} の翻訳"):
        while True:
            # ダブルクオーテーションが含まれている場合、翻訳失敗することがあるので対処
            if '"' in entry.msgid:
                raise Exception(f"{lang}: {entry.msgid}")

            # 翻訳を依頼
            translation = gemini_translate(
                text=entry.msgid,
                lang=lang,
            )

            # 翻訳結果を保存
            entry.msgstr = translation

            # fuzzy フラグを削除
            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
            sleep(GEMINI_SLEEP_TIME)

            if entry.msgid != entry.msgstr:
                break

            # 中国語は重複を許可
            if lang in ZH:
                break

            logger.debug(f"[main] Translation: {entry.msgid} -> {entry.msgstr}")
            logger.warning("[main] Translation failed")
            po.save(path)
            po = polib.pofile(path)

    po.save(path)


def main():
    # Generate translation messages
    os.system(
        f"cd {BASE_DIR} && pybabel extract --omit-header --no-wrap --sort-by-file -F babel.cfg -o {POT_FILE} ."
    )
    os.system(
        f"cd {BASE_DIR} && pybabel update --omit-header --no-wrap -i {POT_FILE} -d {LOCALE_DIR}"
    )

    for lang in BABEL_SUPPORTED_LOCALES:
        path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

        # ファイルが存在しない場合は新規作成
        if not os.path.exists(path):
            os.system(
                f"cd {BASE_DIR} && pybabel init --omit-header --no-wrap -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
            )

        translate(path, lang)

    # Compile translation messages
    os.system(f"cd {BASE_DIR} && pybabel compile --statistics -d {LOCALE_DIR}")
    logger.info("[main] Translation process finished")


if __name__ == "__main__":
    main()
