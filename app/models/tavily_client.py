import hashlib
import os
from typing import Optional

from tavily import TavilyClient

EXCLUDE_DOMAINS = [
    "tiktok.com",
    "reddit.com",
    "swissbeatbox.com",
    "gbbinfo-jpn.onrender.com",
]


class TavilyService:
    def __init__(self):
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEYが設定されていません")
        self._tavily_api_key = tavily_api_key
        self._client: Optional[TavilyClient] = None

    @property
    def client(self) -> TavilyClient:
        if self._client is None:
            self._client = TavilyClient(self._tavily_api_key)
        return self._client

    def beatboxer_research(self, beatboxer_name: str):
        query = f"{beatboxer_name} beatbox"
        result = self.client.search(
            query=query,
            max_results=12,
            include_answer="basic",
            include_favicon=True,
            exclude_domains=EXCLUDE_DOMAINS,
        )
        return result

    def suggest_page_url(self, year: int, question: str) -> dict:
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        question_hash = hashlib.md5(question.encode()).hexdigest()
        cache_key = f"suggest_url_{year}_{question_hash}"

        # キャッシュから取得を試行 あるなら返す
        cached_data = flask_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        results = self.client.search(
            query=f"{year} {question}",
            max_results=5,
            include_domains=["gbbinfo-jpn.onrender.com"],
        )

        # キャッシュに保存
        flask_cache.set(cache_key, results)

        return results


# グローバルインスタンス
tavily_service = TavilyService()
