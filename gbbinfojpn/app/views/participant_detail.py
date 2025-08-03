import re
from urllib.parse import parse_qs, urlparse

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.app.models.tavily_client import tavily_service


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


def get_beatboxer_name(beatboxer_id: int):
    # 出場者名を取得
    participant_data = supabase_service.get_data(
        table="Participant",
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
    beatboxer_id: int | None = None, beatboxer_name: str | None = None
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
        beatboxer_name = get_beatboxer_name(beatboxer_id)

    # キャッシュキーを作成（スペースやその他の特殊文字を安全な文字に置換）
    cache_key = (
        f"tavily_search_{re.sub(r'[^a-zA-Z0-9_-]', '_', beatboxer_name.strip())}"
    )

    # キャッシュから結果を取得
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # Tavily APIで検索を実行
    search_results = tavily_service.search(beatboxer_name)["results"]

    # 結果を格納するリスト
    account_urls = []  # アカウントURL（@を含むもの）
    final_urls = []  # 最終的な選定URL
    youtube_embed_url = ""

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
                    f"https://www.youtube.com/embed/{video_id}?amp;controls=0"
                )

        # ステップ1: アカウントURLの収集（@を含むURLまたはタイトル）
        is_account_url = ("@" in item["url"]) or ("@" in item["title"])
        is_new_domain = primary_domain not in account_domains_seen

        if is_account_url and is_new_domain:
            account_urls.append(item)
            account_domains_seen.add(primary_domain)

        # ステップ2: プライマリドメインごとの代表URLを収集
        is_new_domain = primary_domain not in final_domains_seen
        is_not_account_url = item not in account_urls

        if is_new_domain and is_not_account_url:
            final_urls.append(item)
            final_domains_seen.add(primary_domain)

    # 3件以上取得できた場合はおわり
    if len(final_urls) >= 3:
        result = (account_urls, final_urls, youtube_embed_url)
        # キャッシュに保存（24時間）
        cache.set(cache_key, result, timeout=None)
        return result

    # ステップ3: 最低3件を確保するため、不足分を検索順で補完
    for item in search_results:
        is_not_included = item not in final_urls and item not in account_urls

        if is_not_included:
            final_urls.append(item)
            if len(final_urls) >= 3:
                break

    result = (account_urls, final_urls, youtube_embed_url)
    # キャッシュに保存（24時間）
    cache.set(cache_key, result, timeout=None)
    return result


def post_beatboxer_tavily_search(request: HttpRequest):
    beatboxer_id = request.POST.get("beatboxer_id")

    account_urls, final_urls, youtube_embed_url = beatboxer_tavily_search(
        beatboxer_id=beatboxer_id
    )

    data = {
        "account_urls": account_urls,
        "final_urls": final_urls,
        "youtube_embed_url": youtube_embed_url,
    }
    return JsonResponse(data)


def participant_detail_view(request: HttpRequest):
    id = request.GET.get("id")  # 出場者ID
    mode = request.GET.get("mode")  # single, team, team_member

    if mode == "team_member":
        beatboxer_data = supabase_service.get_data(
            table="ParticipantMember",
            columns=["participant", "name"],
            join_tables={
                "Country": ["iso_code", "names"],
                "Category": ["name"],
                "Participant": [
                    "id",
                    "name",
                    "year",
                    "category",
                    "is_cancelled",
                ],
            },
            filters={
                "id": id,
            },
        )
        beatboxer_detail = beatboxer_data[0]

        # 名前は大文字に変換
        beatboxer_detail["name"] = beatboxer_detail["name"].upper()

        # 設定言語に合わせて国名を取得
        language = request.LANGUAGE_CODE
        beatboxer_detail["country"] = beatboxer_detail["Country"]["names"][language]
        beatboxer_detail.pop("Country")

        # メンバーの情報に無い情報を追加
        beatboxer_detail["year"] = beatboxer_detail["Participant"]["year"]
        beatboxer_detail["category"] = beatboxer_detail["Category"]["name"]
        beatboxer_detail.pop("Category")
        beatboxer_detail["is_cancelled"] = beatboxer_detail["Participant"][
            "is_cancelled"
        ]

        context = {
            "beatboxer_detail": beatboxer_detail,
            "mode": mode,
        }
        return render(request, "others/participant_detail.html", context)

    # 1人部門 or チーム部門のチームについての情報を取得
    beatboxer_data = supabase_service.get_data(
        table="Participant",
        columns=[
            "id",
            "name",
            "year",
            "category",
            "iso_code",
            "ticket_class",
            "is_cancelled",
        ],
        join_tables={
            "Country": ["iso_code", "names"],
            "Category": ["name"],
            "ParticipantMember": ["id", "name"],
        },
        filters={
            "id": id,
        },
    )

    beatboxer_detail = beatboxer_data[0]

    # 名前は大文字に変換
    beatboxer_detail["name"] = beatboxer_detail["name"].upper()

    # 設定言語に合わせて国名を取得
    language = request.LANGUAGE_CODE
    beatboxer_detail["country"] = beatboxer_detail["Country"]["names"][language]
    beatboxer_detail.pop("Country")

    # 部門名を取得
    beatboxer_detail["category"] = beatboxer_detail["Category"]["name"]
    beatboxer_detail.pop("Category")

    context = {
        "beatboxer_detail": beatboxer_detail,
        "mode": mode,
    }
    return render(request, "others/participant_detail.html", context)
