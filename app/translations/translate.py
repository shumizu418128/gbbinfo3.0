import os
from time import sleep

import polib
from google import genai
from pydantic import BaseModel
from tqdm import tqdm

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


class Translation(BaseModel):
    translation: str


def gemini_translate(text, lang):
    client = genai.Client()
    prompt = f"""Translate the following text to {lang}.
Important instructions:
1. Return ONLY the translated text
2. Do NOT add any placeholders or variables that weren't in the original text
3. Do NOT translate any text that looks like {{variable_name}} - keep it exactly as is
4. Do NOT add any explanatory text or notes

Text to translate: {text}"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": Translation,
        },
    )
    return response.parsed.translation


def translate(path, lang):
    try:
        print(f"Processing {lang}: {path}")
        po = polib.pofile(path)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        raise

    # エスケープが異常に多い場合は fuzzy フラグを付与
    for entry in po.translated_entries():
        if "\\" in entry.msgstr:
            entry.flags.append("fuzzy")

    po.save(path)  # プレースホルダーの検証結果を保存
    po = polib.pofile(path)  # 再度ファイルを読み込む

    # 翻訳が必要なエントリを処理
    untranslated_entries = po.untranslated_entries() + po.fuzzy_entries()
    msgids = [entry.msgid for entry in untranslated_entries]
    if msgids:
        print(msgids)

    for entry in tqdm(untranslated_entries, desc=f"{lang} の翻訳"):
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
        sleep(2)

    po.save(path)


def main():
    # Generate translation messages
    os.system(f"cd {BASE_DIR} && pybabel extract --omit-header --no-wrap --sort-by-file -F babel.cfg -o {POT_FILE} .")
    os.system(f"cd {BASE_DIR} && pybabel update --omit-header --no-wrap -i {POT_FILE} -d {LOCALE_DIR}")

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
    print("Finished")


if __name__ == "__main__":
    main()
