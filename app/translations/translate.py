import os
import re
from time import sleep

import polib
from google import genai
from pydantic import BaseModel
from tqdm import tqdm

from app.main import BABEL_SUPPORTED_LOCALES

BASE_DIR = os.path.abspath("app")
LOCALE_DIR = os.path.join(BASE_DIR, "translations")
POT_FILE = os.path.join(BASE_DIR, "messages.pot")
CONFIG_FILE = os.path.join(BASE_DIR, "babel.cfg")


def extract_placeholders(text):
    """
    文字列からプレースホルダー `{name}` を抽出します。

    Args:
        text (str): プレースホルダーを抽出する対象の文字列。

    Returns:
        set: 文字列から抽出されたプレースホルダー名のセット。
    """
    pattern = r"\{([^}]+)\}"
    validation = set(re.findall(pattern, text)) or "placeholder" in text.lower()
    return validation


def validate_placeholders(msgid, msgstr):
    """
    プレースホルダーの検証を行います。

    Args:
        msgid (str): 元の文字列 (翻訳元)。
        msgstr (str): 翻訳後の文字列。

    Returns:
        bool: プレースホルダーが一致する場合は True、一致しない場合は False。
    """
    src_placeholders = extract_placeholders(msgid)
    trans_placeholders = extract_placeholders(msgstr)

    if src_placeholders != trans_placeholders:
        return False
    return True


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
        model="gemini-2.5-flash",
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

    for entry in po:
        if entry.msgstr:  # 翻訳が存在する場合のみチェック
            result = validate_placeholders(entry.msgid, entry.msgstr)

            # プレースホルダーが一致しない場合は fuzzy フラグを追加
            if not result:
                entry.flags.append("fuzzy")

    po.save(path)  # プレースホルダーの検証結果を保存
    po = polib.pofile(path)  # 再度ファイルを読み込む

    # 翻訳が必要なエントリを処理
    untranslated_entries = po.untranslated_entries() + po.fuzzy_entries()
    msgids = [entry.msgid for entry in untranslated_entries]
    if msgids:
        print(msgids)

    for entry in tqdm(untranslated_entries, desc=f"{lang} の翻訳"):
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
    os.system(f"cd {BASE_DIR} && pybabel extract -F babel.cfg -o {POT_FILE} .")
    os.system(f"cd {BASE_DIR} && pybabel update -i {POT_FILE} -d {LOCALE_DIR}")

    for lang in BABEL_SUPPORTED_LOCALES:
        path = os.path.join(LOCALE_DIR, lang, "LC_MESSAGES", "messages.po")

        # ファイルが存在しない場合は新規作成
        if not os.path.exists(path):
            os.system(
                f"cd {BASE_DIR} && pybabel init -i {POT_FILE} -d {LOCALE_DIR} -l {lang}"
            )

        translate(path, lang)

    # Compile translation messages
    os.system(f"cd {BASE_DIR} && pybabel compile -d {LOCALE_DIR}")
    print("Finished")


if __name__ == "__main__":
    main()
