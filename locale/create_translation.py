#!/usr/bin/env python3
"""
包括的な翻訳システム
HTMLファイルから文字列を抽出し、Gemini API/DeepL APIで翻訳して、poファイルに書き出し、コンパイルまで実行する

# 全言語をGemini APIで翻訳
python locale/create_translation.py

# 特定言語のみDeepL APIで翻訳
python locale/create_translation.py --api deepl --languages en ko

# コンパイルのみ
python locale/create_translation.py --compile-only

# ドライランモード
python locale/create_translation.py --dry-run

# 詳細ログ
python locale/create_translation.py --verbose
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Set

import django
from django.conf import settings
from pydantic import BaseModel

# Djangoの設定を読み込む
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gbbinfojpn.settings")

django.setup()


# Gemini API用の翻訳レスポンススキーマ
class TranslationResponse(BaseModel):
    """Gemini API用の翻訳レスポンススキーマ"""

    translation: str


# APIクライアントのインポート
try:
    from google import genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print(
        "Warning: Gemini APIが利用できません（pip install google-genai でインストールしてください）"
    )

try:
    import deepl

    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False
    print(
        "Warning: DeepL APIが利用できません（pip install deepl でインストールしてください）"
    )


class DjangoMakemessagesExtractor:
    """Django makemessagesコマンドを使用した翻訳対象文字列抽出クラス"""

    def __init__(self):
        self.locale_path = Path(settings.LOCALE_PATHS[0])
        # 設定からロケールコードを取得（日本語以外）
        self.languages = [code for code, _ in settings.LANGUAGES if code != "ja"]

    def run_makemessages(self) -> bool:
        """Django makemessagesコマンドを実行"""
        try:
            # 各言語ごとにmakemessagesを実行
            for lang_code in self.languages:
                subprocess.run(
                    [
                        "python",
                        "manage.py",
                        "makemessages",
                        "--locale",
                        lang_code,
                        "--ignore=venv",  # 仮想環境を無視
                        "--ignore=node_modules",  # Node.jsモジュールを無視
                        "--extension=html,py",  # HTML, Pythonファイルを対象
                    ],
                    check=True,
                    cwd=settings.BASE_DIR,
                )

            print("Django makemessagesコマンド実行完了")
            return True

        except subprocess.CalledProcessError as e:
            print(f"makemessagesコマンドエラー: {e}")
            return False

    def extract_strings_from_po(self, lang_code: str) -> Set[str]:
        """POファイルから翻訳対象文字列を抽出"""
        po_file = self.locale_path / lang_code / "LC_MESSAGES" / "django.po"
        strings = set()

        if not po_file.exists():
            return strings

        try:
            with open(po_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            current_msgid = ""
            state = None  # None, 'msgid', 'msgstr'

            for line in lines:
                line = line.strip()

                if line.startswith("msgid "):
                    # 前のエントリを保存
                    if current_msgid and current_msgid != "":
                        strings.add(current_msgid)

                    # 新しいmsgidを開始
                    current_msgid = line[6:].strip('"')
                    state = "msgid"

                elif line.startswith("msgstr "):
                    # msgstrの開始、msgidの終了
                    if current_msgid and current_msgid != "":
                        strings.add(current_msgid)
                    current_msgid = ""
                    state = "msgstr"

                elif line.startswith('"') and line.endswith('"') and state == "msgid":
                    # msgidの継続行
                    current_msgid += line[1:-1]

            # 最後のエントリを保存
            if current_msgid and current_msgid != "":
                strings.add(current_msgid)

        except Exception as e:
            print(f"POファイル読み込みエラー {po_file}: {e}")

        return strings

    def get_all_translation_strings(self) -> Set[str]:
        """すべての翻訳対象文字列を取得"""
        # makemessagesを実行
        if not self.run_makemessages():
            return set()

        # 各言語のPOファイルから文字列を抽出
        all_strings = set()
        for lang_code in self.languages:
            strings = self.extract_strings_from_po(lang_code)
            all_strings.update(strings)

        return all_strings

    def get_translation_files_list(self) -> list:
        """翻訳対象ファイル一覧を取得（makemessagesが処理したファイル）"""
        # makemessagesが処理するファイルのパターンを返す
        files = []

        # テンプレートディレクトリのHTMLファイル
        template_dirs = [
            Path(settings.BASE_DIR) / "gbbinfojpn" / "app" / "templates",
            Path(settings.BASE_DIR) / "gbbinfojpn" / "database" / "templates",
        ]

        for template_dir in template_dirs:
            if template_dir.exists():
                for html_file in template_dir.rglob("*.html"):
                    try:
                        # {% trans %}や{% blocktrans %}が含まれているかチェック
                        with open(html_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "{% trans" in content or "{% blocktrans" in content:
                                relative_path = str(html_file.relative_to(template_dir))
                                files.append(f"templates/{relative_path}")
                    except Exception:
                        continue

        # Pythonファイル
        python_dirs = [
            Path(settings.BASE_DIR) / "gbbinfojpn" / "app" / "views",
            Path(settings.BASE_DIR) / "gbbinfojpn" / "database" / "views",
            Path(settings.BASE_DIR) / "gbbinfojpn" / "common",
        ]

        for python_dir in python_dirs:
            if python_dir.exists():
                for py_file in python_dir.rglob("*.py"):
                    if "__pycache__" in str(py_file):
                        continue
                    try:
                        # _() が含まれているかチェック
                        with open(py_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "_(" in content:
                                relative_path = str(py_file.relative_to(python_dir))
                                files.append(
                                    f"python/{python_dir.name}/{relative_path}"
                                )
                    except Exception:
                        continue

        return sorted(files)


class TranslationService:
    """翻訳サービスの基底クラス"""

    def translate(self, text: str, target_lang: str) -> str:
        raise NotImplementedError


class GeminiTranslationService(TranslationService):
    """Gemini APIを使用した翻訳サービス"""

    def __init__(self):
        if not GEMINI_AVAILABLE:
            raise ImportError("Gemini APIが利用できません")

        # 言語コードマッピング
        self.lang_mapping = {
            "ko": "Korean",
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "fr": "French",
            "hi": "Hindi",
            "hu": "Hungarian",
            "it": "Italian",
            "ms": "Malay",
            "no": "Norwegian",
            "ta": "Tamil",
            "th": "Thai",
            "zh_Hans": "Simplified Chinese",
            "zh_Hant": "Traditional Chinese",
        }

        # Gemini APIキーの確認
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません")

        # Gemini Clientの初期化
        self.client = genai.Client(api_key=self.api_key)

        # レートリミット用: 最後のリクエスト時刻
        self.last_request_time = 0

        # 日本語文字検出用の正規表現
        self.japanese_patterns = {
            "hiragana": re.compile(r"[\u3040-\u309F]"),  # ひらがな
            "katakana": re.compile(r"[\u30A0-\u30FF]"),  # カタカナ
            "kanji": re.compile(r"[\u4E00-\u9FAF]"),  # 漢字（CJK統合漢字）
        }

    def _contains_japanese_chars(self, text: str, target_lang: str) -> bool:
        """
        翻訳結果に日本語文字が含まれているかチェック
        中国語（zh-Hans, zh-Hant）と韓国語（ko）の場合は漢字チェックを無効にする
        """
        # ひらがなチェック
        if self.japanese_patterns["hiragana"].search(text):
            return True

        # カタカナチェック
        if self.japanese_patterns["katakana"].search(text):
            return True

        # 漢字チェック（中国語・韓国語の場合はスキップ）
        if target_lang not in ["zh_Hans", "zh_Hant", "ko"]:
            if self.japanese_patterns["kanji"].search(text):
                return True

        return False

    def translate(self, text: str, target_lang: str, max_retries: int = 3) -> str:
        """テキストを指定言語に翻訳（品質チェック付き）"""
        if target_lang not in self.lang_mapping:
            return text

        target_language = self.lang_mapping[target_lang]

        for attempt in range(max_retries):
            # レートリミット: 2秒間隔を保証
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < 2.1:
                sleep_time = 2.1 - time_since_last_request
                print(f"    レートリミット待機中: {sleep_time:.1f}秒")
                time.sleep(sleep_time)

            try:
                # 翻訳プロンプト
                prompt = f"""Translate the following text to {target_language}.
Preserve any HTML tags and variables (like {{{{ var }}}}) exactly as they appear.

Text to translate:
{text}"""

                # リクエスト時刻を記録
                self.last_request_time = time.time()

                # Gemini APIを直接呼び出し（Pydanticスキーマ使用）
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=prompt,
                    config={
                        "temperature": 0.3,
                        "max_output_tokens": 1000,
                        "response_mime_type": "application/json",
                        "response_schema": TranslationResponse,
                    },
                )

                if response and response.parsed:
                    # Pydanticオブジェクトから翻訳結果を取得
                    translation_obj: TranslationResponse = response.parsed
                    translated = translation_obj.translation.strip()

                    if not translated:
                        print(f"翻訳結果が空です (Gemini): {text}")
                        continue

                    # 翻訳品質チェック: 日本語文字が含まれていないかチェック
                    if self._contains_japanese_chars(translated, target_lang):
                        print(
                            f"翻訳失敗 (日本語文字検出, 試行 {attempt + 1}/{max_retries}): {translated}"
                        )
                        if attempt < max_retries - 1:
                            continue  # リトライ
                        else:
                            raise Exception("翻訳品質チェックに失敗しました。")

                    return translated

                else:
                    print(f"翻訳失敗 (Gemini): {text}")
                    if attempt < max_retries - 1:
                        continue
                    return text

            except Exception as e:
                print(f"Gemini翻訳エラー (試行 {attempt + 1}/{max_retries}): {e}")
                print(f"対象テキスト: {text}")
                if attempt < max_retries - 1:
                    continue
                return text

        return text


class DeepLTranslationService(TranslationService):
    """DeepL APIを使用した翻訳サービス"""

    def __init__(self):
        if not DEEPL_AVAILABLE:
            raise ImportError("DeepL APIが利用できません")

        api_key = os.environ.get("DEEPL_API_KEY")
        if not api_key:
            raise ValueError("DEEPL_API_KEYが設定されていません")

        self.translator = deepl.Translator(api_key)

        # 言語コードマッピング
        self.lang_mapping = {
            "ko": "KO",
            "en": "EN-US",
            "de": "DE",
            "es": "ES",
            "fr": "FR",
            "hi": "HI",
            "hu": "HU",
            "it": "IT",
            "no": "NB",
            "zh_Hans": "ZH",
            "zh_Hant": "ZH",
        }

        # 日本語文字検出用の正規表現
        self.japanese_patterns = {
            "hiragana": re.compile(r"[\u3040-\u309F]"),  # ひらがな
            "katakana": re.compile(r"[\u30A0-\u30FF]"),  # カタカナ
            "kanji": re.compile(r"[\u4E00-\u9FAF]"),  # 漢字（CJK統合漢字）
        }

    def _contains_japanese_chars(self, text: str, target_lang: str) -> bool:
        """
        翻訳結果に日本語文字が含まれているかチェック
        中国語（zh-Hans, zh-Hant）と韓国語（ko）の場合は漢字チェックを無効にする
        """
        # ひらがなチェック
        if self.japanese_patterns["hiragana"].search(text):
            return True

        # カタカナチェック
        if self.japanese_patterns["katakana"].search(text):
            return True

        # 漢字チェック（中国語・韓国語の場合はスキップ）
        if target_lang not in ["zh_Hans", "zh_Hant", "ko"]:
            if self.japanese_patterns["kanji"].search(text):
                return True

        return False

    def translate(self, text: str, target_lang: str, max_retries: int = 3) -> str:
        """テキストを指定言語に翻訳（品質チェック付き）"""
        if target_lang not in self.lang_mapping:
            return text

        for attempt in range(max_retries):
            try:
                result = self.translator.translate_text(
                    text, source_lang="JA", target_lang=self.lang_mapping[target_lang]
                )
                translated = result.text.strip()

                if not translated:
                    print(f"翻訳結果が空です (DeepL): {text}")
                    continue

                # 翻訳品質チェック: 日本語文字が含まれていないかチェック
                if self._contains_japanese_chars(translated, target_lang):
                    print(
                        f"翻訳失敗 (日本語文字検出, 試行 {attempt + 1}/{max_retries}): {translated}"
                    )
                    if attempt < max_retries - 1:
                        continue  # リトライ
                    else:
                        print(
                            f"最大試行回数に達しました。元のテキストを返します: {text}"
                        )
                        return text

                return translated

            except Exception as e:
                print(f"DeepL翻訳エラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue
                return text

        return text


class POFileManager:
    """POファイルの管理クラス"""

    def __init__(self):
        self.locale_path = Path(settings.LOCALE_PATHS[0])
        # 設定からロケールコードを取得（日本語以外）
        self.languages = [code for code, _ in settings.LANGUAGES if code != "ja"]

    def read_existing_po(self, lang_code: str) -> Dict[str, str]:
        """既存のPOファイルから翻訳済み文字列を読み込み"""
        po_file = self.locale_path / lang_code / "LC_MESSAGES" / "django.po"
        translations = {}

        if not po_file.exists():
            return translations

        try:
            with open(po_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            current_msgid = ""
            current_msgstr = ""
            state = None  # None, 'msgid', 'msgstr'

            for line in lines:
                line = line.strip()

                if line.startswith("msgid "):
                    # 前のエントリを保存
                    if current_msgid and current_msgstr:
                        translations[current_msgid] = current_msgstr

                    # 新しいmsgidを開始
                    current_msgid = line[6:].strip('"')
                    current_msgstr = ""
                    state = "msgid"

                elif line.startswith("msgstr "):
                    current_msgstr = line[7:].strip('"')
                    state = "msgstr"

                elif line.startswith('"') and line.endswith('"') and state:
                    # 継続行
                    content = line[1:-1]
                    if state == "msgid":
                        current_msgid += content
                    elif state == "msgstr":
                        current_msgstr += content

                elif line == "" or line.startswith("#"):
                    # 空行またはコメント - エントリの終了
                    if current_msgid and current_msgstr:
                        translations[current_msgid] = current_msgstr
                    state = None

            # 最後のエントリを保存
            if current_msgid and current_msgstr:
                translations[current_msgid] = current_msgstr

        except Exception as e:
            print(f"POファイル読み込みエラー {po_file}: {e}")

        return translations

    def escape_po_string(self, text: str) -> str:
        """POファイル用に文字列をエスケープ"""
        # バックスラッシュを最初にエスケープ
        text = text.replace("\\", "\\\\")
        # ダブルクォートをエスケープ
        text = text.replace('"', '\\"')
        # 改行をエスケープ
        text = text.replace("\n", "\\n")
        # タブをエスケープ
        text = text.replace("\t", "\\t")
        return text

    def write_po_file(
        self, lang_code: str, strings: Set[str], translations: Dict[str, str]
    ):
        """POファイルを書き出し"""
        po_dir = self.locale_path / lang_code / "LC_MESSAGES"
        po_dir.mkdir(parents=True, exist_ok=True)
        po_file = po_dir / "django.po"

        # POファイルのヘッダー
        header = f"""# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2025-01-01 00:00+0000\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"Language: {lang_code}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

"""

        try:
            with open(po_file, "w", encoding="utf-8") as f:
                f.write(header)

                for string in sorted(strings):
                    translation = translations.get(string, "")

                    # 文字列をエスケープ
                    escaped_string = self.escape_po_string(string)
                    escaped_translation = self.escape_po_string(translation)

                    f.write(f'msgid "{escaped_string}"\n')
                    f.write(f'msgstr "{escaped_translation}"\n\n')

            print(f"POファイル作成完了: {po_file}")

        except Exception as e:
            print(f"POファイル書き込みエラー {po_file}: {e}")

    def compile_po_files(self):
        """すべてのPOファイルをコンパイル"""
        for lang_code in self.languages:
            po_file = self.locale_path / lang_code / "LC_MESSAGES" / "django.po"
            if po_file.exists():
                try:
                    subprocess.run(
                        [
                            "python",
                            "manage.py",
                            "compilemessages",
                            "--locale",
                            lang_code,
                        ],
                        check=True,
                        cwd=settings.BASE_DIR,
                    )
                    print(f"コンパイル完了: {lang_code}")
                except subprocess.CalledProcessError as e:
                    print(f"コンパイルエラー {lang_code}: {e}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="包括的翻訳システム - HTMLファイルから文字列を抽出し、翻訳してpoファイルを生成・コンパイル",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # すべての言語をGemini APIで翻訳
  python create_translation.py

  # 特定の言語のみDeepL APIで翻訳
  python create_translation.py --api deepl --languages en ko

  # 文字列抽出のみ実行
  python create_translation.py --extract-only

  # コンパイルのみ実行
  python create_translation.py --compile-only

  # ドライランモード（実際の変更は行わない）
  python create_translation.py --dry-run

  # 詳細ログ表示
  python create_translation.py --verbose

環境変数:
  GEMINI_API_KEY: Gemini API使用時に必要
  DEEPL_API_KEY: DeepL API使用時に必要

注記:
  翻訳処理実行時に、locale/translation_target_files.txt に翻訳対象ファイル一覧が自動出力されます。
        """,
    )
    parser.add_argument(
        "--api",
        choices=["gemini", "deepl"],
        default="gemini",
        help="使用する翻訳API (default: gemini)",
    )
    parser.add_argument(
        "--languages", nargs="+", help="翻訳対象言語コード (default: すべて)"
    )
    parser.add_argument(
        "--extract-only", action="store_true", help="文字列抽出のみ実行"
    )
    parser.add_argument(
        "--compile-only", action="store_true", help="コンパイルのみ実行"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="実際の翻訳は行わず、処理内容のみ表示"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細なログを表示")

    args = parser.parse_args()

    try:
        # 翻訳対象言語の決定
        target_languages = args.languages or [
            code for code, _ in settings.LANGUAGES if code != "ja"
        ]

        print("=== 包括的翻訳システム開始 ===")
        print(f"翻訳API: {args.api}")
        print(f"対象言語: {target_languages}")
        if args.dry_run:
            print("*** DRY RUNモード - 実際の変更は行いません ***")

        if args.compile_only:
            # コンパイルのみ
            print("\nコンパイルのみモード")
            po_manager = POFileManager()
            po_manager.compile_po_files()
            print("=== コンパイル完了 ===")
            return

        # 1. Django makemessagesを使用した文字列抽出
        print("\n1. Django makemessagesコマンドで翻訳対象文字列を抽出中...")
        extractor = DjangoMakemessagesExtractor()
        unique_strings = extractor.get_all_translation_strings()

        print(f"抽出完了: {len(unique_strings)} 個の文字列")

        # 翻訳対象ファイル一覧を自動出力（機械読み込み用）
        translation_files = extractor.get_translation_files_list()
        output_file = (
            Path(settings.BASE_DIR) / "locale" / "translation_target_files.txt"
        )
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for file_path in translation_files:
                    f.write(f"{file_path}\n")

            if args.verbose:
                print(f"翻訳対象ファイル一覧を出力: {output_file}")
                print(f"対象ファイル数: {len(translation_files)}")

        except Exception as e:
            print(f"ファイル一覧出力エラー: {e}")

        if args.extract_only:
            print("\n抽出された文字列:")
            for string in sorted(unique_strings):
                print(f"  - {string}")
            print(f"\n合計: {len(unique_strings)} 個の翻訳対象文字列")
            return

        if not unique_strings:
            print("翻訳対象の文字列が見つかりませんでした。")
            return

        # 2. 翻訳サービスの初期化
        print(f"\n2. {args.api.upper()} 翻訳サービスを初期化中...")
        try:
            if args.api == "gemini":
                translation_service = GeminiTranslationService()
            else:
                translation_service = DeepLTranslationService()
        except Exception as e:
            print(f"翻訳サービス初期化エラー: {e}")
            print("APIキーが正しく設定されているか確認してください。")
            return

        # 3. POファイル管理の初期化
        po_manager = POFileManager()

        # 4. 各言語の翻訳処理
        for lang_code in target_languages:
            print(f"\n3. {lang_code} の翻訳処理中...")

            # 既存の翻訳を読み込み
            existing_translations = po_manager.read_existing_po(lang_code)
            print(f"既存翻訳: {len(existing_translations)} 個")

            # 新しい翻訳が必要な文字列を特定
            new_strings = unique_strings - set(existing_translations.keys())
            print(f"新規翻訳対象: {len(new_strings)} 個")

            if not new_strings:
                print(f"  {lang_code}: 新規翻訳対象なし")
                po_manager.write_po_file(
                    lang_code, unique_strings, existing_translations
                )
                continue

            # 翻訳実行
            all_translations = existing_translations.copy()

            if args.dry_run:
                print(f"  [DRY RUN] {len(new_strings)} 個の文字列を翻訳する予定")
                if args.verbose:
                    for string in list(new_strings)[:10]:  # 最初の10個だけ表示
                        print(f"    - {string}")
                    if len(new_strings) > 10:
                        print(f"    ... 他 {len(new_strings) - 10} 個")
            else:
                success_count = 0
                for i, string in enumerate(new_strings, 1):
                    if args.verbose or i % 10 == 0:  # 10個ごとまたは詳細モードで表示
                        print(f"  翻訳中 ({i}/{len(new_strings)}): {string[:50]}...")
                    try:
                        translation = translation_service.translate(string, lang_code)
                        if translation and translation != string:
                            all_translations[string] = translation
                            success_count += 1
                        else:
                            if args.verbose:
                                print("    警告: 翻訳されませんでした")
                            all_translations[string] = ""  # 空の翻訳として保存
                    except Exception as e:
                        if args.verbose:
                            print(f"    エラー: {e}")
                        all_translations[string] = ""

                print(f"  翻訳完了: {success_count}/{len(new_strings)} 個")

            # POファイル書き出し
            if not args.dry_run:
                po_manager.write_po_file(lang_code, unique_strings, all_translations)

        # 5. コンパイル
        if not args.dry_run:
            print("\n4. POファイルをコンパイル中...")
            po_manager.compile_po_files()
        else:
            print("\n4. [DRY RUN] POファイルのコンパイルをスキップ")

        print("\n=== 翻訳システム完了 ===")
        if not args.dry_run:
            print("すべての翻訳ファイルが読み込み可能な状態になりました。")
        else:
            print("DRY RUNモードで実行しました。実際のファイルは変更されていません。")

    except KeyboardInterrupt:
        print("\n\n処理が中断されました。")
    except Exception as e:
        print(f"\n予期せぬエラーが発生しました: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
