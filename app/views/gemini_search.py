import random
import re
from threading import Thread

import pykakasi
from flask import jsonify, request
from rapidfuzz import process

from app.models.gemini_client import gemini_service
from app.models.spreadsheet_client import spreadsheet_service
from app.views.config.gemini_search_config import SEARCH_CACHE

HIRAGANA = "H"
KATAKANA = "K"
KANJI = "J"
ALPHABET = "a"

kakasi = pykakasi.kakasi()
kakasi.setMode(HIRAGANA, ALPHABET)  # ひらがなをローマ字に変換
kakasi.setMode(KATAKANA, ALPHABET)  # カタカナをローマ字に変換
kakasi.setMode(KANJI, ALPHABET)  # 漢字をローマ字に変換
converter = kakasi.getConverter()


# MARK: URL作成
def create_url(year: int, url: str, parameter: str | None, name: str | None):
    """
    指定された情報に基づいてレスポンスURLを作成します。

    Args:
        year (int): 質問が関連する年。
        url (str): ベースURL。
        parameter (str): スクロール位置を示すパラメータ。
        name (str): 質問に含まれている名前。

    Returns:
        str: 作成されたURL。
    """
    response_url = url

    # パラメータがNoneの場合はNoneを空文字に変換
    if parameter.lower() == "none" or parameter.lower() == "null":
        parameter = ""

    # nameも同様
    if name.lower() == "none" or name.lower() == "null":
        name = ""

    # topのNoneは問い合わせに変更
    if "top" in url and parameter == "":
        parameter = "contact"

    # 7toSmoke最新情報の場合は7tosmokeこれだけガイドページに変更
    if url == "/others/7tosmoke" and parameter in ["latest_info", None]:
        response_url = f"/{year}/top_7tosmoke"

    # パラメータがある場合は追加
    if parameter != "" and parameter != "search_participants":
        response_url += f"?scroll={parameter}"

    # participantsのsearch_participantsが指定された場合はvalueに質問を追加
    if parameter == "search_participants" and name != "":
        # search_participantsのとき、nameがある場合のみ追加
        response_url += "?scroll=search_participants"

        # 英数字表記かどうか判定
        # 記号も対象・Ωは"Sound of Sony Ω"の入力対策
        alphabet_pattern = r'^[a-zA-Z0-9 \-!@#$%^&*()_+=~`<>?,.\/;:\'"\\|{}[\]Ω]+'
        match_alphabet = re.match(alphabet_pattern, name)

        # 英数字表記の場合、大文字に変換して追加
        if match_alphabet:
            response_url += f"&value={match_alphabet.group().upper()}"

        # それ以外の場合、ローマ字に変換して追加
        else:
            romaji_name = converter.do(name)

            # 一応ちゃんと変換できたか確認
            match_alphabet = re.match(alphabet_pattern, romaji_name)
            if match_alphabet:
                response_url += f"&value={romaji_name.upper()}"
            else:
                response_url += f"&value={name}"

    return response_url


def post_gemini_search(year: int):
    question = request.form.get("question")

    # questionがNoneまたは空文字の場合のチェック
    if not question:
        return jsonify({"error": "Question is required"}), 400

    response = {}
    url = ""

    if question.upper() in SEARCH_CACHE:
        url = SEARCH_CACHE[question.upper()].replace("__year__", str(year))

    else:
        # 最大5回リトライ
        retry = 5
        for _ in range(retry):
            gemini_response = gemini_service.ask_sync(year, question)
            if gemini_response:
                url = create_url(
                    year,
                    gemini_response["url"],
                    gemini_response["parameter"],
                    gemini_response["name"],
                )
                break

    # スプシに記録
    Thread(
        target=spreadsheet_service.record_question, args=(year, question, url)
    ).start()

    response = {
        "url": url,
    }
    return jsonify(response)


def post_gemini_search_suggestion():
    input = request.form.get("input", "").strip()

    # 下処理：inputから4桁・2桁の年削除
    year = re.search(r"\d{4}", input)
    year_2 = re.search(r"\d{2}", input)
    if year:
        year = year.group()
        input = input.replace(year, "")
    if year_2:
        year_2 = year_2.group()
        input = input.replace(year_2, "")

    # 下処理：inputから空白削除
    input = input.strip().upper().replace("GBB", "")

    # rapidfuzzで類似度を計算し、上位3件を取得
    cache_keys = list(SEARCH_CACHE.keys())
    random.shuffle(cache_keys)
    suggestions = process.extract(input, cache_keys, limit=3, score_cutoff=1)

    # rapidfuzzの結果から検索候補を取得
    suggestions = [result[0] for result in suggestions]

    return jsonify({"suggestions": suggestions})
