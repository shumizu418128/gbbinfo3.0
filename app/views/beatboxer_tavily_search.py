import json
import re
from urllib.parse import parse_qs, urlparse

from flask import jsonify, request, session

from app.models.gemini_client import gemini_service
from app.models.supabase_client import supabase_service
from app.models.tavily_client import tavily_service
from app.views.config.gemini_search_config import PROMPT_TRANSLATE


def get_primary_domain(url: str) -> str:
    """
    指定されたURLからプライマリドメイン（例: example.com）を抽出します。

    Args:
        url (str): 対象のURL

    Returns:
        str: プライマリドメイン
    """
    parsed_url = urlparse(url)
    full_domain = parsed_url.netloc.lower()
    domain_parts = full_domain.split(".")
    if len(domain_parts) >= 2:
        return ".".join(domain_parts[-2:])
    else:
        return full_domain


def get_beatboxer_name(beatboxer_id: int, mode: str = "single"):
    """
    出場者IDから出場者名を取得し、大文字で返します。

    Args:
        beatboxer_id (int): 取得対象の出場者ID。
        mode (str, optional): 取得モード。"single"の場合は個人出場者、"team_member"の場合はチームメンバーとして取得します。デフォルトは"single"。

    Returns:
        str: 出場者名（大文字）。

    Raises:
        IndexError: 指定したIDに該当する出場者が存在しない場合。
    """
    # 出場者名を取得
    participant_data = supabase_service.get_data(
        table="Participant",
        columns=["name"],
        filters={
            "id": beatboxer_id,
        },
    )
    if mode == "team_member":
        participant_data = supabase_service.get_data(
            table="ParticipantMember",
            columns=["name"],
            filters={
                "id": beatboxer_id,
            },
        )
    beatboxer_name = participant_data[0]["name"].upper()
    return beatboxer_name


def extract_youtube_video_id(url):
    """YouTubeのURLからvideo_idを抽出する。

    Args:
        url (str): YouTube動画のURL。

    Returns:
        str or None: video_id（11文字）を返す。見つからない場合はNone。
    """
    parsed = urlparse(url)
    if "youtube" in parsed.netloc:
        # watch?v=VIDEO_ID
        qs = parse_qs(parsed.query)
        if "v" in qs and re.match(r"^[a-zA-Z0-9_-]{11}$", qs["v"][0]):
            return qs["v"][0]
        # /embed/VIDEO_ID
        m = re.match(r"^/embed/([a-zA-Z0-9_-]{11})", parsed.path)
        if m:
            return m.group(1)
    elif "youtu.be" in parsed.netloc:
        # youtu.be/VIDEO_ID
        m = re.match(r"^/([a-zA-Z0-9_-]{11})", parsed.path)
        if m:
            return m.group(1)
    return None


def beatboxer_tavily_search(
    beatboxer_id: int | None = None,
    beatboxer_name: str | None = None,
    mode: str = "single",
):
    """
    指定された出場者IDに基づき、Tavily検索APIを利用して関連するURLリストを取得します。

    検索結果から以下のルールでURLを選定します:
    1. アカウントURL枠：URLまたはタイトルに「@」が含まれるもの 制限なし
    2. プライマリドメインごとに最初に出現した検索結果 制限なし
    3. 上記1,2で3件未満の場合、残りは検索順位順で追加し、最低3件となるようにする

    また、上記とは別に、YouTube動画URLを1件取得

    Args:
        beatboxer_id (int): 検索対象の出場者ID
        beatboxer_name (str): 検索対象の出場者名

    Returns:
        tuple: (アカウントURLリスト, 最終的な選定URLリスト, YouTube動画URL)

    Raises:
        IndexError: 指定したIDの出場者が存在しない場合

    """
    # パラメータのバリデーション
    if beatboxer_id is None and beatboxer_name is None:
        raise ValueError("beatboxer_idまたはbeatboxer_nameが必要です")

    # beatboxer_nameが指定されていない場合は、beatboxer_idから取得
    if beatboxer_name is None:
        beatboxer_name = get_beatboxer_name(beatboxer_id, mode)

    # キャッシュキーを作成（スペースやその他の特殊文字を安全な文字に置換）
    cache_key = (
        f"tavily_search_{re.sub(r'[^a-zA-Z0-9_-]', '_', beatboxer_name.strip())}"
    )

    # キャッシュとデータベースから結果を取得
    tavily_response = supabase_service.get_tavily_data(cache_key=cache_key)

    # キャッシュがない場合はTavilyで検索して保存
    if len(tavily_response) == 0:
        tavily_response = tavily_service.search(beatboxer_name)
        supabase_service.insert_tavily_data(
            cache_key=cache_key,
            search_result=tavily_response,
        )

    search_results_unfiltered = tavily_response["results"]

    search_results = []

    # 禁止ワードが一切含まれないもののみsearch_resultsに追加
    BAN_WORDS = ["HATEN", "BEATCITY", "JPN CUP"]
    for item in search_results_unfiltered:
        title_upper = item["title"].upper()
        url_upper = item["url"].upper()
        content_upper = item["content"].upper()
        if not any(
            ban_word in title_upper
            or ban_word in url_upper
            or ban_word in content_upper
            for ban_word in BAN_WORDS
        ):
            search_results.append(item)

    # 結果を格納するリスト
    account_urls = []  # アカウントURL（@を含むもの）
    final_urls = []  # 最終的な選定URL
    youtube_embed_url = ""
    original_youtube_embed_url = ""

    # 処理済みのプライマリドメインを記録
    account_domains_seen = set()
    final_domains_seen = set()

    # 各検索結果にプライマリドメイン情報を追加
    for item in search_results:
        primary_domain = get_primary_domain(item["url"])
        item["primary_domain"] = primary_domain

        # YouTube動画URLの場合、video_idを取得
        if primary_domain == "youtube.com" and youtube_embed_url == "":
            video_id = extract_youtube_video_id(item["url"])
            if video_id:
                youtube_embed_url = (
                    f"https://www.youtube.com/embed/{video_id}?controls=0&hd=1&vq=hd720"
                )
                original_youtube_embed_url = item["url"]

        # ステップ1: アカウントURLの収集（@を含むURLまたはタイトル）
        youtube_channel_pattern = r"^(https?:\/\/)?(www\.)?youtube\.com\/(c\/|channel\/|user\/|@)[a-zA-Z0-9_-]+\/?$"
        instagram_account_pattern = (
            r"^(https?:\/\/)?(www\.)?instagram\.com\/[a-zA-Z0-9_.]+\/?$"
        )
        facebook_account_pattern = (
            r"^(https?:\/\/)?(www\.)?facebook\.com\/[a-zA-Z0-9_.]+\/?$"
        )
        is_account_url = (
            ("@" in item["url"])
            or ("@" in item["title"])
            or bool(re.match(youtube_channel_pattern, item["url"]))
            or bool(re.match(instagram_account_pattern, item["url"]))
            or bool(re.match(facebook_account_pattern, item["url"]))
        )
        is_new_domain = primary_domain not in account_domains_seen

        if is_account_url and is_new_domain:
            account_urls.append(item)
            account_domains_seen.add(primary_domain)

        # ステップ2: プライマリドメインごとの代表URLを収集
        is_new_domain = primary_domain not in final_domains_seen
        is_not_account_url = item not in account_urls
        is_not_youtube_url = item["url"] != original_youtube_embed_url

        if is_new_domain and is_not_account_url and is_not_youtube_url:
            final_urls.append(item)
            final_domains_seen.add(primary_domain)

    # 3件以上取得できた場合はおわり
    if len(final_urls) >= 3:
        result = (account_urls, final_urls, youtube_embed_url)
        return result

    # ステップ3: 最低3件を確保するため、不足分を検索順で補完
    for item in search_results:
        is_not_included = item not in final_urls and item not in account_urls
        is_not_youtube_url = item["url"] != original_youtube_embed_url

        if is_not_included and is_not_youtube_url:
            final_urls.append(item)
            if len(final_urls) >= 3:
                break

    result = (account_urls, final_urls, youtube_embed_url)
    return result


def post_beatboxer_tavily_search():
    """
    ビートボクサーの検索リクエストを処理し、関連するURLとアカウント情報を取得します。

    リクエストボディから beatboxer_id と mode を取得し、Tavily検索を実行して
    アカウントURL、一般URL、YouTube埋め込みURLを返します。

    Returns:
        JSON: 以下の構造を持つレスポンス
            - account_urls: SNSアカウント等のURL一覧
            - final_urls: 一般的なウェブサイトURL一覧
            - youtube_embed_url: YouTube埋め込み用URL
    """
    beatboxer_id = request.json.get("beatboxer_id")
    mode = request.json.get("mode", "single")

    account_urls, final_urls, youtube_embed_url = beatboxer_tavily_search(
        beatboxer_id=beatboxer_id, mode=mode
    )

    data = {
        "account_urls": account_urls,
        "final_urls": final_urls,
        "youtube_embed_url": youtube_embed_url,
    }
    return jsonify(data)


def translate_tavily_answer(beatboxer_id: int, mode: str, language: str):
    # まずキャッシュを取得
    beatboxer_name = get_beatboxer_name(beatboxer_id, mode)
    cache_key = (
        f"tavily_search_{re.sub(r'[^a-zA-Z0-9_-]', '_', beatboxer_name.strip())}"
    )

    # 内部キャッシュを取得
    from app.main import flask_cache

    # 内部キャッシュがあれば返す
    internal_cache_answer = flask_cache.get(cache_key + "_answer_translation")
    if internal_cache_answer:
        try:
            return internal_cache_answer[language]
        except KeyError:
            pass

    # 外部キャッシュを取得
    cached_answer = supabase_service.get_tavily_data(
        cache_key=cache_key, column="answer_translation"
    )

    # あれば返す
    if len(cached_answer) > 0:
        try:
            # 最初の要素を取得
            if isinstance(cached_answer, list):
                cached_answer = cached_answer[0]
            if isinstance(cached_answer, str):
                cached_answer = json.loads(cached_answer)
            translated_answer = cached_answer[language]
            return translated_answer
        except KeyError:
            pass

    # なければ生成
    search_result = supabase_service.get_tavily_data(cache_key=cache_key)
    try:
        # search_resultがリストの場合、最初の要素を取得
        if isinstance(search_result, list):
            if len(search_result) == 0:
                return ""  # データが存在しない場合
            search_result = search_result[0]

        # answerフィールドにアクセス
        answer = search_result["answer"]
    except (KeyError, TypeError, IndexError):
        return ""  # answerの生成は他エンドポイントの責任

    # 翻訳
    prompt = PROMPT_TRANSLATE.format(text=answer, lang=language)
    response = gemini_service.ask_sync(prompt)
    if isinstance(response, list):
        response = response[0]
    try:
        translated_answer = response["translated_text"]
    except Exception:
        return ""

    # キャッシュに保存
    # 翻訳結果を保存するためのディクショナリを準備
    translation_cache = {}
    # 既存のキャッシュがあれば取得
    existing_cache = supabase_service.get_tavily_data(
        cache_key=cache_key, column="answer_translation"
    )
    if len(existing_cache) > 0:
        try:
            if isinstance(existing_cache, list):
                existing_cache = existing_cache[0]
            if isinstance(existing_cache, str):
                translation_cache = json.loads(existing_cache)
            elif isinstance(existing_cache, dict):
                translation_cache = existing_cache
        except (json.JSONDecodeError, TypeError):
            translation_cache = {}

    translation_cache[language] = translated_answer

    supabase_service.update_translated_answer(
        cache_key=cache_key,
        translated_answer=translation_cache,
    )

    return translated_answer


def post_answer_translation():
    beatboxer_id = request.json.get("beatboxer_id")
    mode = request.json.get("mode", "single")
    language = session["language"]

    translated_answer = translate_tavily_answer(beatboxer_id, mode, language)
    return jsonify({"answer": translated_answer})
