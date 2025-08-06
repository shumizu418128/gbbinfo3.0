import json

from gbbinfojpn.app.views.beatboxer_tavily_search import beatboxer_tavily_search

"""
python -m gbbinfojpn.app.tests.tavily_test
"""

if __name__ == "__main__":
    beatboxer_name = "THORSEN"

    account_urls, final_urls, youtube_thumbnail_url = beatboxer_tavily_search(
        beatboxer_name=beatboxer_name
    )
    print(json.dumps(account_urls, ensure_ascii=False, indent=2))
    print("--------------------------------")
    print(json.dumps(final_urls, ensure_ascii=False, indent=2))
    print("--------------------------------")
    print(youtube_thumbnail_url)
