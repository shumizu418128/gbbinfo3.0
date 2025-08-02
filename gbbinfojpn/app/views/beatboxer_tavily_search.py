from urllib.parse import urlparse

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


def beatboxer_tavily_search(
    beatboxer_id: int | None = None, beatboxer_name: str | None = None
):
    """
    指定された出場者IDに基づき、Tavily検索APIを利用して関連するURLリストを取得します。

    検索結果から以下のルールでURLを選定します:
    1. アカウントURL枠：URLまたはタイトルに「@」が含まれるもの 制限なし
    2. プライマリドメインごとに最初に出現した検索結果 制限なし
    3. 上記1,2で3件未満の場合、残りは検索順位順で追加し、最低3件となるようにする

    Args:
        beatboxer_id (int): 検索対象の出場者ID

    Returns:
        tuple[list[dict], list[dict]]: 選定されたURL情報の辞書リスト（Tavily APIの検索結果アイテム形式）

    Raises:
        IndexError: 指定したIDの出場者が存在しない場合

    """
    if beatboxer_id is None and beatboxer_name is None:
        raise ValueError("beatboxer_idまたはbeatboxer_nameが必要です")

    if beatboxer_name is None:
        beatboxer_name = get_beatboxer_name(beatboxer_id)

    # tavilyで検索
    result = tavily_service.search(beatboxer_name)["results"]

    account_urls = []
    account_urls_primary_domain = {}
    final_urls = []
    final_urls_primary_domain = {}

    # 1. アカウントURLを確認
    for item in result:
        # プライマリドメインを取得し、もとの結果辞書に追加
        primary_domain = get_primary_domain(item["url"])
        item["primary_domain"] = primary_domain

        # アカウントURLかどうかを確認
        is_account_url = ("@" in item["url"]) or ("@" in item["title"])

        # アカウントURLとしてまだ追加されていない場合のみ追加
        is_new_domain_for_account_urls = (
            primary_domain not in account_urls_primary_domain
        )

        if is_account_url and is_new_domain_for_account_urls:
            account_urls.append(item)
            account_urls_primary_domain[primary_domain] = item

        # まだそのプライマリドメインが記録されていない場合のみ追加（最初に見つかったものが1位）
        if primary_domain not in final_urls_primary_domain and item not in account_urls:
            final_urls_primary_domain[primary_domain] = item

    # 2. プライマリドメインごとの1位をfinal_urlsに追加（重複チェック）
    for domain_item in final_urls_primary_domain.values():
        if domain_item not in final_urls and domain_item not in account_urls:
            final_urls.append(domain_item)

    # URLが3つ以上取得できた場合はおわり
    if len(final_urls) >= 3:
        return (account_urls, final_urls)

    # 3つ未満の場合は、残りは検索順位順で追加し、最低3つとする
    for item in result:
        if item not in final_urls and item not in account_urls:
            final_urls.append(item)
            if len(final_urls) >= 3:
                break

    return (account_urls, final_urls)
