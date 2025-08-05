import re
from urllib.parse import parse_qs, quote, urlparse

from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render

from gbbinfojpn.app.models.supabase_client import supabase_service
from gbbinfojpn.app.models.tavily_client import tavily_service
from gbbinfojpn.common.filter_eq import Operator
from gbbinfojpn.common.participant_edit import team_multi_country, wildcard_rank_sort


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
    search_results = supabase_service.get_tavily_data(cache_key)

    # ないならTavilyで検索して保存
    if len(search_results) == 0:
        search_results = tavily_service.search(beatboxer_name)
        supabase_service.insert_tavily_data(cache_key, search_results)

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
        youtube_channel_pattern = r"^(https?:\/\/)?(www\.)?youtube\.com\/(c\/|channel\/|user\/|@)?[a-zA-Z0-9_-]+(\/.*)?$"
        instagram_account_pattern = (
            r"^(https?:\/\/)?(www\.)?instagram\.com\/[a-zA-Z0-9_.]+\/?$"
        )
        is_account_url = (
            ("@" in item["url"])
            or ("@" in item["title"])
            or bool(re.match(youtube_channel_pattern, item["url"]))
            or bool(re.match(instagram_account_pattern, item["url"]))
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


def post_beatboxer_tavily_search(request: HttpRequest):
    beatboxer_id = request.POST.get("beatboxer_id")
    mode = request.POST.get("mode", "single")

    account_urls, final_urls, youtube_embed_url = beatboxer_tavily_search(
        beatboxer_id=beatboxer_id, mode=mode
    )

    data = {
        "account_urls": account_urls,
        "final_urls": final_urls,
        "youtube_embed_url": youtube_embed_url,
    }
    return JsonResponse(data)


def participant_detail_view(request: HttpRequest):
    try:
        id = request.GET["id"]  # 出場者ID
        mode = request.GET["mode"]  # single, team, team_member
    except KeyError:
        # id, modeが無い場合、ルートにリダイレクト
        return redirect("/")

    # チームメンバーの場合、情報を取得
    if mode == "team_member":
        beatboxer_data = supabase_service.get_data(
            table="ParticipantMember",
            columns=["id", "participant", "name"],
            join_tables={
                "Country": ["iso_code", "names"],
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
        beatboxer_detail["Participant"]["name"] = beatboxer_detail["Participant"][
            "name"
        ].upper()

        # 設定言語に合わせて国名を取得
        language = request.LANGUAGE_CODE
        beatboxer_detail["country"] = beatboxer_detail["Country"]["names"][language]
        beatboxer_detail.pop("Country")

        # メンバーの情報に無い情報を追加
        beatboxer_detail["year"] = beatboxer_detail["Participant"]["year"]
        beatboxer_detail["is_cancelled"] = beatboxer_detail["Participant"][
            "is_cancelled"
        ]

    # 1人部門 or チーム部門のチームについての情報を取得
    else:
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
                "Category": ["id", "name"],
                "ParticipantMember": ["id", "name", "Country(names)"],
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

        # 複数国籍のチームの場合、国名をまとめる
        if beatboxer_detail["iso_code"] == 9999:
            beatboxer_detail = team_multi_country(beatboxer_detail, language)

        # 1国籍のチームの場合、国名を取得
        else:
            beatboxer_detail["country"] = beatboxer_detail["Country"]["names"][language]
            beatboxer_detail.pop("Country")

        # 部門名を取得
        beatboxer_detail["category"] = beatboxer_detail["Category"]["name"]

        # チームメンバーの国名を取得
        if beatboxer_detail["ParticipantMember"]:
            for member in beatboxer_detail["ParticipantMember"]:
                member["country"] = member["Country"]["names"][language]
                member["name"] = member["name"].upper()

    # 過去の出場履歴を取得
    past_participation_data = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "year", "is_cancelled", "category"],
        order_by="year",
        join_tables={
            "Category": ["name"],
            "ParticipantMember": ["id"],
        },
        filters={
            f"name__{Operator.MATCH_IGNORE_CASE}": beatboxer_detail["name"],
        },
    )
    past_participation_member_data = supabase_service.get_data(
        table="ParticipantMember",
        columns=["name"],
        join_tables={
            "Participant": [
                "id",
                "name",
                "year",
                "is_cancelled",
                "Category(name)",
                "category",
            ],
        },
        filters={
            f"name__{Operator.MATCH_IGNORE_CASE}": beatboxer_detail["name"],
        },
    )

    past_data = []

    # MATCH_IGNORE_CASE演算子は大文字小文字を区別しない部分一致であるため、完全一致の確認を行う
    for past_participation in past_participation_data:
        if past_participation["name"].upper() == beatboxer_detail["name"]:
            past_participation_mode = (
                "single" if past_participation["ParticipantMember"] is None else "team"
            )
            past_data.append(
                {
                    "id": past_participation["id"],
                    "year": past_participation["year"],
                    "name": past_participation["name"].upper(),
                    "category": past_participation["Category"]["name"],
                    "category_id": past_participation["category"],
                    "is_cancelled": past_participation["is_cancelled"],
                    "mode": past_participation_mode,
                }
            )
    for past_participation_member in past_participation_member_data:
        if past_participation_member["name"].upper() == beatboxer_detail["name"]:
            past_data.append(
                {
                    "id": past_participation_member["Participant"]["id"],
                    "year": past_participation_member["Participant"]["year"],
                    "name": past_participation_member["Participant"]["name"].upper(),
                    "category": past_participation_member["Participant"]["Category"][
                        "name"
                    ],
                    "category_id": past_participation_member["Participant"]["category"],
                    "is_cancelled": past_participation_member["Participant"][
                        "is_cancelled"
                    ],
                    "mode": "team",
                }
            )
    past_data.sort(key=lambda x: (x["year"], x["category_id"]))

    # 対象Beatboxerと同じ年・部門の出場者一覧を取得
    # 部門を調べる
    if mode == "team_member":
        category_id = beatboxer_detail["Participant"]["category"]
    else:
        category_id = beatboxer_detail["Category"]["id"]

    same_year_category_participants = supabase_service.get_data(
        table="Participant",
        columns=["id", "name", "is_cancelled", "ticket_class", "iso_code"],
        join_tables={
            "Country": ["names"],
            "ParticipantMember": ["id", "name", "Country(names)"],
        },
        filters={
            "year": beatboxer_detail["year"],
            "category": category_id,
        },
    )

    same_year_category_edited = []
    for participant in same_year_category_participants:
        participant["name"] = participant["name"].upper()
        if participant["iso_code"] == 9999:
            participant = team_multi_country(participant, language)
        else:
            participant["country"] = participant["Country"]["names"][language]
            participant.pop("Country")
        same_year_category_edited.append(participant)

    same_year_category_edited.sort(
        key=lambda x: (
            x["is_cancelled"],  # キャンセルした人は下
            x["iso_code"] == 0,  # 出場者未定枠は下
            "Wildcard" in x["ticket_class"],  # Wildcard通過者は下
            wildcard_rank_sort(x),  # Wildcardのランキング順にする
            "GBB" not in x["ticket_class"],  # GBBによるシードは上
        )
    )

    same_year_category_mode = "single" if mode == "single" else "team"
    genspark_query = quote(beatboxer_detail["name"] + " beatbox")

    context = {
        "beatboxer_detail": beatboxer_detail,
        "mode": mode,
        "past_participation_data": past_data,
        "same_year_category_participants": same_year_category_edited,
        "same_year_category_mode": same_year_category_mode,
        "genspark_query": genspark_query,
    }

    return render(request, "others/participant_detail.html", context)
