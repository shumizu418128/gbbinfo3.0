import os
import random
import re
import unicodedata
from threading import Thread

from flask import jsonify, request
from rapidfuzz import process

from app.config.config import PROMPT, SEARCH_CACHE
from app.models.gemini_client import gemini_service
from app.models.spreadsheet_client import spreadsheet_service

others_url_list = [
    file_name.replace(".html", "") for file_name in os.listdir("app/templates/others")
]


# MARK: URL作成
def create_url(year: int, url: str, parameter: str | None):
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

    # topのNoneは問い合わせに変更
    if "top" in url and parameter == "":
        parameter = "contact"

    # othersのURLは年度情報を削除
    if url.replace(f"/{year}/", "") in others_url_list:
        response_url = url.replace(f"/{year}/", "/others/")

    # 7toSmoke最新情報の場合は7tosmokeこれだけガイドページに変更
    if url == "/others/7tosmoke" and parameter in ["latest_info", ""]:
        response_url = f"/{year}/top_7tosmoke"

    # パラメータがある場合は追加
    if parameter != "":
        response_url += f"?scroll={parameter}"

    return response_url


# MARK: gemini
def post_gemini_search(year: int, IS_LOCAL: bool, IS_PULL_REQUEST: bool):
    """Gemini検索APIのエンドポイント。

    Geminiサービスを利用して、与えられた質問に対するURLを返します。
    質問がキャッシュに存在する場合はキャッシュからURLを取得し、存在しない場合はGeminiサービスに問い合わせます。
    また、ローカル環境やプルリクエスト環境でない場合は、質問と結果のURLをスプレッドシートに記録します。

    Args:
        year (int): 対象となる年。
        IS_LOCAL (bool): ローカル環境かどうかのフラグ。
        IS_PULL_REQUEST (bool): プルリクエスト環境かどうかのフラグ。

    Returns:
        flask.Response: URLを含むJSONレスポンス。
            例: {"url": "/2024/top_7tosmoke"}
            質問が未入力の場合は400エラーとエラーメッセージを返します。
    """
    question = request.json.get("question")

    # questionがNoneまたは空文字の場合のチェック
    if not question:
        return jsonify({"error": "Question is required"}), 400

    response = {}
    url = ""

    # 全角数字・アルファベットを半角に変換
    question = unicodedata.normalize("NFKC", question)

    if question.upper() in SEARCH_CACHE:
        url = SEARCH_CACHE[question.upper()].replace("__year__", str(year))

    else:
        print(f"question: {question}", flush=True)
        prompt = PROMPT.format(year=year, question=question)

        # 最大5回リトライ
        retry = 5
        i = 0
        while True:
            gemini_response = gemini_service.ask(prompt)
            # urlを正しく作れた場合
            if gemini_response.get("url") is not None:
                url = create_url(
                    year,
                    gemini_response["url"],
                    gemini_response["parameter"],
                )
                break
            # 503エラーは、失敗とはみなさず、リトライする
            if gemini_response.get("error_code") == 503:
                continue
            # 失敗し続けた場合は500エラーを返す
            i += 1
            if i >= retry:
                return jsonify({"url": ""}), 500

    # スプシに記録
    if IS_LOCAL is False and IS_PULL_REQUEST is False:
        Thread(
            target=spreadsheet_service.record_question, args=(year, question, url)
        ).start()

    response = {
        "url": url,
    }
    return jsonify(response)


# MARK: suggest
def post_gemini_search_suggestion():
    """
    Gemini検索サジェストAPIエンドポイント。

    ユーザーからの入力文(input)を受け取り、年情報（4桁または2桁）や不要な文字列（"GBB"など）を除去した上で、
    キャッシュに登録されている質問候補（SEARCH_CACHEのキー）との類似度をrapidfuzzで計算し、
    類似度が高い上位3件のサジェスト候補を返します。

    Args:
        なし（リクエストボディにJSON形式で"input"を含める）

    Returns:
        flask.Response: サジェスト候補リストを含むJSONレスポンス。
            例: {"suggestions": ["候補1", "候補2", "候補3"]}
    """
    data = request.get_json(silent=True) or {}
    input = str(data.get("input", "")).strip()

    # 下処理：inputから4桁・2桁の年削除
    year = re.search(r"\d{4}", input)
    year_2 = re.search(r"\d{2}", input)
    if year:
        year = year.group()
        input = input.replace(year, "")
    if year_2:
        year_2 = year_2.group()
        input = input.replace(year_2, "")

    # 下処理：inputから空白削除と"GBB"除去
    input = input.strip().upper().replace("GBB", "")

    # rapidfuzzで類似度を計算し、上位3件を取得
    cache_keys = list(SEARCH_CACHE.keys())
    random.shuffle(cache_keys)
    suggestions = process.extract(input, cache_keys, limit=3, score_cutoff=1)

    # rapidfuzzの結果から検索候補を取得
    suggestions = [result[0] for result in suggestions]

    return jsonify({"suggestions": suggestions})
