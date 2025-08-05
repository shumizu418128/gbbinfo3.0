import os
from typing import Optional

from tavily import TavilyClient

EXCLUDE_DOMAINS = [
    "tiktok.com",
    "reddit.com",
    "swissbeatbox.com",
    "onrender.com",
    "fandom.com",
    "wikipedia.org",
    "swiki.jp",
]


class TavilyService:
    def __init__(self):
        self._client: Optional[TavilyClient] = None

    @property
    def client(self) -> TavilyClient:
        if self._client is None:
            tavily_api_key = os.getenv("TAVILY_API_KEY")

            if not tavily_api_key:
                raise ValueError("TAVILY_API_KEYが設定されていません")

            self._client = TavilyClient(tavily_api_key)

        return self._client

    def search(self, beatboxer_name: str):
        query = f"{beatboxer_name} beatbox"
        result = self.client.search(
            query=query,
            max_results=10,
            include_favicon=True,
            exclude_domains=EXCLUDE_DOMAINS,
        )
        return result["results"]


# グローバルインスタンス
tavily_service = TavilyService()
