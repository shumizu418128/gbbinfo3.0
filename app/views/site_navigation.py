import os
import random
import re
import unicodedata
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from flask import jsonify, request
from rapidfuzz import process

from app.config.config import SEARCH_CACHE
from app.models.spreadsheet_client import spreadsheet_service
from app.models.tavily_client import tavily_service

others_url_list = [
    file_name.replace(".html", "") for file_name in os.listdir("app/templates/others")
]


# MARK: URL
def create_url(results: list[dict], year: int) -> str:
    """Tavilyの検索結果から適切なURLを生成する。

    検索結果から年に一致するURLを優先的に選択し、見つからない場合は
    最初の結果を使用します。URLからlangクエリパラメータを削除し、
    外部URLを内部URL（パスのみ）に変換します。

    Args:
        results (list[dict]): Tavilyの検索結果リスト。各要素は"url"キーを含む辞書。
        year (int): 優先的にマッチさせる対象年。URLに含まれる年を検索します。

    Returns:
        str: 生成された内部URL。クエリパラメータがある場合は含まれます。
            結果が空の場合は空文字列を返します。
    """
    url = ""

    # yearに一致するURLを優先的に探す
    for result in results:
        if str(year) in result.get("url", ""):
            url = result.get("url", "")
            break

    # yearに一致するものがない場合は最初の結果を使用
    if not url and results:
        url = results[0].get("url", "")

    # クエリパラメータから"lang"を削除
    if "?" in url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("lang", None)  # langパラメータを削除
        new_query = urlencode(params, doseq=True)
        url = urlunparse(parsed._replace(query=new_query))

    # tavilyは常に外部URLなので、内部URLに変換
    parsed = urlparse(url)
    url = parsed.path
    if parsed.query:
        url += "?" + parsed.query

    return url


# MARK: search
def post_search(year: int, IS_LOCAL: bool, IS_PULL_REQUEST: bool):
    """検索APIのエンドポイント。

    ユーザーからの質問を受け取り、適切なページURLを返します。

    Args:
        year (int): 対象となる年。URLの生成とキャッシュの置換に使用されます。
        IS_LOCAL (bool): ローカル環境かどうかのフラグ。
            Trueの場合はスプレッドシートへの記録をスキップします。
        IS_PULL_REQUEST (bool): プルリクエスト環境かどうかのフラグ。
            Trueの場合はスプレッドシートへの記録をスキップします。

    Returns:
        flask.Response: URLを含むJSONレスポンス。
            成功時: {"url": "/2024/top_7tosmoke"} (HTTPステータス200)
            エラー時: {"error": "Question is required"} (HTTPステータス400)
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
        results = tavily_service.suggest_page_url(question)

        url = create_url(results, year)

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
def post_search_suggestion():
    """検索サジェストAPIエンドポイント。

    ユーザーの入力に基づいて、検索候補を提案します。

    Args:
        なし。リクエストボディにJSON形式で以下のパラメータを含めます:
            - input (str): ユーザーの入力文字列

    Returns:
        flask.Response: サジェスト候補リストを含むJSONレスポンス（HTTPステータス200）。
            例: {"suggestions": ["WORLD CHAMPIONSHIP", "RULE", "TICKET"]}
            最大3件の候補を返します。該当がない場合は空リストを返します。
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
