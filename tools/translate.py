import os
import re
import sys
from time import sleep

import httpcore
import httpx
import polib
from google import genai
from pydantic import BaseModel
from tqdm import tqdm

# main.pyからBABEL_SUPPORTED_LOCALESを取得するためのパス設定
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.main import BABEL_SUPPORTED_LOCALES as _ALL_LOCALES

# 翻訳対象言語（日本語を除外）
BABEL_SUPPORTED_LOCALES = [locale for locale in _ALL_LOCALES if locale != "ja"]

# tools/ディレクトリから app/ディレクトリを参照するようにパスを修正
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
LOCALE_DIR = os.path.join(BASE_DIR, "translations")
POT_FILE = os.path.join(BASE_DIR, "messages.pot")
CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")


GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_SLEEP_TIME = 4


class Translation(BaseModel):
    """翻訳結果を格納するためのPydanticモデル。

    Attributes:
        translation (str): 翻訳されたテキスト
    """

    translation: str


def gemini_translate(text, lang):
    """Gemini APIを使用してテキストを翻訳する。

    Args:
        text (str): 翻訳対象のテキスト
        lang (str): 翻訳先の言語コード

    Returns:
        str: 翻訳されたテキスト。翻訳に失敗した場合は元のテキストを返す
    """
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
            # httpx/httpcore関連のエラーの場合はリトライ
            if isinstance(
                e,
                (
                    httpx.RemoteProtocolError,
                    httpcore.RemoteProtocolError,
                    httpx.ConnectError,
                    httpx.ReadTimeout,
                ),
            ):
                print(
                    f"Network error occurred: {type(e).__name__}. Retrying...",
                    flush=True,
                )
                continue

            # エラー内に 'retryDelay': '44s' のような表記がある場合、数字を取り出してスリープ
            error_str = str(e)
            match = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
            if match:
                delay_sec = int(match.group(1))
                if delay_sec == 0:
                    delay_sec = GEMINI_SLEEP_TIME
                print(f"429 Rate limit exceeded. Retrying after {delay_sec} seconds")
                sleep(delay_sec)
                continue

            try:
                error = e.get("error")
                if error and error.get("code") == 503:
                    print(
                        f"503 Service Unavailable. Retrying after {GEMINI_SLEEP_TIME} seconds",
                        flush=True,
                    )
                    sleep(GEMINI_SLEEP_TIME)
                    continue
            except Exception:
                pass
            raise

    try:
        return response.parsed.translation
    except Exception:
        return text


def reuse_obsolete_translations(po):
    """コメントアウトされた翻訳（obsolete entries）を再利用する。

    Args:
        po: polib.POFile オブジェクト
    """
    # コメントアウトされたエントリを取得
    obsolete_entries = po.obsolete_entries()

    if not obsolete_entries:
        return

    print(f"Found {len(obsolete_entries)} obsolete translations to check for reuse")

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

                    reused_count += 1
                    print(f"Reused translation for: {obsolete_entry.msgid[:50]}...")

    print(f"Reused {reused_count} translations from obsolete entries")


def prioritize_existing_translations(po, untranslated_entries):
    """既存の翻訳を優先的に使用する。

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

                # 未翻訳リストから削除
                untranslated_entries.remove(entry)
                prioritized_count += 1
                print(f"Prioritized existing translation for: {entry.msgid[:50]}...")
                break

    print(f"Prioritized {prioritized_count} existing translations")


ZH = ["zh_Hans_CN", "zh_Hant_TW"]


def translation_check(entry, lang):
    """翻訳結果の品質をチェックし、必要に応じてfuzzyフラグを付与する。

    Args:
        entry: polib.POEntry オブジェクト
        lang (str): 言語コード
    """
    if entry.msgid == entry.msgstr:  # 同じ言葉で
        # 中国語ではない場合はフラグを付与
        if lang not in ZH:
            entry.flags.append("fuzzy")

        # 中国語でも、10文字以上またはひらがな・カタカナを含む場合は fuzzy フラグを付与
        elif len(entry.msgid) > 10 or re.search(
            r"[\u3041-\u3096\u30A1-\u30FA]", entry.msgid
        ):
            entry.flags.append("fuzzy")

    # 翻訳結果がひらがな・カタカナを含む場合は fuzzy フラグを付与
    if re.search(r"[\u3041-\u3096\u30A1-\u30FA]", entry.msgstr):
        entry.flags.append("fuzzy")


def translate(path, lang):
    """指定された言語のPOファイルを翻訳する。

    Args:
        path (str): POファイルのパス
        lang (str): 言語コード
    """
    try:
        print(f"Processing {lang}: {path}")

        # ファイルが存在しない場合はスキップ
        if not os.path.exists(path):
            print(f"Skipping {lang}: file does not exist at {path}")
            return

        po = polib.pofile(path)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        print(f"Skipping {lang} due to error")
        return

    # コメントアウトされた翻訳を再利用
    reuse_obsolete_translations(po)

    # エスケープが異常に多い場合は fuzzy フラグを付与
    for entry in po.translated_entries():
        translation_check(entry, lang)

    po.save(path)  # プレースホルダーの検証結果を保存
    po = polib.pofile(path)  # 再度ファイルを読み込む

    # 翻訳が必要なエントリを処理
    untranslated_entries = po.untranslated_entries() + po.fuzzy_entries()
    msgids = [entry.msgid for entry in untranslated_entries]
    if msgids:
        print(msgids)

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

            # 翻訳結果が変わっていて、ひらがな・カタカナが含まれていない場合成功
            if entry.msgid != entry.msgstr and not re.search(
                r"[\u3041-\u3096\u30A1-\u30FA]", entry.msgstr
            ):
                break

            # 中国語 かつ 原文にひらがな・カタカナが含まれていない場合のみ、翻訳結果がそのままでも成功
            if lang in ZH and not re.search(
                r"[\u3041-\u3096\u30A1-\u30FA]", entry.msgid
            ):
                break

            print(entry.msgid, entry.msgstr, flush=True)
            print("翻訳失敗", flush=True)

        # 翻訳が1つ終わるたびに保存
        po.save(path)


def main():
    """メイン関数：翻訳メッセージの生成、更新、翻訳、コンパイルを実行する。"""
    # Generate translation messages
    os.system(
        f"cd {BASE_DIR} && python -m babel.messages.frontend extract --no-wrap --sort-by-file -F babel.cfg -o {POT_FILE} ."
    )
    os.system(
        f"cd {BASE_DIR} && python -m babel.messages.frontend update --no-wrap -i {POT_FILE} -d {LOCALE_DIR}"
    )

    for lang in BABEL_SUPPORTED_LOCALES:
        path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")
        lang_dir = os.path.join(LOCALE_DIR, lang)

        # 言語ディレクトリが存在しない場合は新規作成
        if not os.path.exists(lang_dir):
            print(f"Creating new locale directory for {lang}")
            result = os.system(
                f"cd {BASE_DIR} && python -m babel.messages.frontend init --no-wrap -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
            )
            if result != 0:
                raise Exception(f"Failed to create locale directory for {lang}")
        # ファイルが存在しない場合も新規作成
        elif not os.path.exists(path):
            print(f"Creating new po file for {lang}")
            result = os.system(
                f"cd {BASE_DIR} && python -m babel.messages.frontend init --no-wrap -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
            )
            if result != 0:
                raise Exception(f"Failed to create po file for {lang}")

        translate(path, lang)

    # Compile translation messages
    os.system(
        f"cd {BASE_DIR} && python -m babel.messages.frontend compile --statistics -d {LOCALE_DIR}"
    )
    print("Finished")


if __name__ == "__main__":
    main()
