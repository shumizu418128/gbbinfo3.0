import logging
import os
from datetime import datetime
from pathlib import Path

from sanic import Sanic
from sanic.response import file
from sanic_ext import Extend

from app.context_processors import (
    common_variables,
    get_locale,
    initialize_background_tasks,
)
from app.views import (
    beatboxer_tavily_search,
    common,
    gemini_search,
    language,
    participant_detail,
    participants,
    result,
    rule,
    search_participants,
    world_map,
)
from app.cache import sanic_cache

from app.cache import sanic_cache

# 基本パスの設定
BASE_DIR = Path(__file__).resolve().parent.parent

# Sanicアプリケーションを作成
app = Sanic("GBBInfo")

# Sanic Extを使用してテンプレートエンジンを設定
app.config.TEMPLATING_PATH_TO_TEMPLATES = str(BASE_DIR / "app" / "templates")
Extend(app)

####################################################################
# MARK: 設定
####################################################################
LANGUAGES = [
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fr", "Français"),
    ("hi", "हिन्दी"),
    ("hu", "Magyar"),
    ("it", "Italiano"),
    ("ms", "Bahasa MY"),
    ("no", "Norsk"),
    ("pt", "Português"),
    ("ta", "தமிழ்"),
    ("th", "ไทย"),
    ("zh_Hans_CN", "简体中文"),
    ("zh_Hant_TW", "繁體中文"),
]
BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]
LAST_UPDATED = "UPDATE " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " JST"


class Config:
    BABEL_DEFAULT_LOCALE = "ja"
    BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "app" / "translations")
    CACHE_DEFAULT_TIMEOUT = 0
    CACHE_TYPE = "simple"
    CACHE_DIR = str(BASE_DIR / "cache")
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    TEMPLATES_AUTO_RELOAD = False


class TestConfig(Config):
    CACHE_TYPE = "null"
    DEBUG = True
    SECRET_KEY = "test"
    TEMPLATES_AUTO_RELOAD = True


# テスト環境かどうかチェック
if os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp":
    print("\n")
    print("******************************************************************")
    print("*                                                                *")
    print("*         GBBINFO-JPN is running in test mode!                   *")
    print("*         Access the application at http://127.0.0.1:10000       *")
    print("*                                                                *")
    print("******************************************************************")
    app.config.update(TestConfig.__dict__)
    IS_LOCAL = True
    IS_PULL_REQUEST = False
else:
    app.config.update(Config.__dict__)
    IS_LOCAL = False
    IS_PULL_REQUEST = os.getenv("IS_PULL_REQUEST") == "true"


from app.cache import sanic_cache

# Flask互換性のため、最小限のflask_cacheオブジェクトを提供
class FlaskCacheCompat:
    def get(self, key):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 非同期コンテキスト内ではNoneを返す（キャッシュスキップ）
                return None
            else:
                return loop.run_until_complete(sanic_cache.get(key))
        except:
            return None
    
    def set(self, key, value, timeout=None):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 非同期コンテキスト内では何もしない
                pass
            else:
                loop.run_until_complete(sanic_cache.set(key, value, timeout))
        except:
            pass

flask_cache = FlaskCacheCompat()


####################################################################
# MARK: ミドルウェア
####################################################################
@app.middleware("request")
async def before_request(request):
    get_locale(BABEL_SUPPORTED_LOCALES)


####################################################################
# MARK: URL ルート
####################################################################
# リダイレクト
app.add_route(common.top_redirect_view_async, "/", methods=["GET"])
app.add_route(
    language.change_language_async,
    "/lang",
    methods=["GET"],
)
app.add_route(common.content_2022_view_async, "/2022/<content>", methods=["GET"])

# POSTリクエスト（暫定的にコメントアウト）
# app.add_route(
#     beatboxer_tavily_search.post_beatboxer_tavily_search_async,
#     "/beatboxer_tavily_search",
#     methods=["POST"],
# )
# app.add_route(
#     gemini_search.post_gemini_search_suggestion_async,
#     "/search_suggestions",
#     methods=["POST"],
# )
# app.add_route(
#     gemini_search.post_gemini_search_async,
#     "/<year:int>/search",
#     methods=["POST"],
# )
# app.add_route(
#     search_participants.post_search_participants_async,
#     "/<year:int>/search_participants",
#     methods=["POST"],
# )
# app.add_route(
#     beatboxer_tavily_search.post_answer_translation_async,
#     "/answer_translation",
#     methods=["POST"],
# )

# データ取得（段階的に有効化）
app.add_route(world_map.world_map_view_async, "/<year:int>/world_map", methods=["GET"])
app.add_route(rule.rules_view_async, "/<year:int>/rule", methods=["GET"])
# app.add_route(
#     participants.participants_view_async, "/<year:int>/participants", methods=["GET"]
# )
# app.add_route(result.result_view_async, "/<year:int>/result", methods=["GET"])
# app.add_route(
#     participants.participants_country_specific_view_async, "/<year:int>/japan", methods=["GET"]
# )
# app.add_route(
#     participants.participants_country_specific_view_async, "/<year:int>/korea", methods=["GET"]
# )
# app.add_route(
#     participant_detail.participant_detail_view_async,
#     "/others/participant_detail",
#     methods=["GET"],
# )

# その他通常ページ
app.add_route(common.other_content_view_async, "/others/<content>", methods=["GET"])
app.add_route(common.content_view_async, "/<year:int>/<content>", methods=["GET"])


####################################################################
# MARK: 静的ファイル
####################################################################
@app.route("/.well-known/discord")
async def discord(request):
    return await file("app/static/discord")


@app.route("/sitemap.xml")
async def sitemap(request):
    return await file("app/static/sitemap.xml", mime_type="application/xml")


@app.route("/robots.txt")
async def robots_txt(request):
    return await file("app/static/robots.txt", mime_type="text/plain")


@app.route("/ads.txt")
async def ads_txt(request):
    return await file("app/static/ads.txt", mime_type="text/plain")


@app.route("/naverc158f3394cb78ff00c17f0a687073317.html")
async def naver_verification(request):
    return await file("app/static/naverc158f3394cb78ff00c17f0a687073317.html")


@app.route("/favicon.ico", methods=["GET"])
async def favicon_ico(request):
    return await file("app/static/favicon.ico", mime_type="image/vnd.microsoft.icon")


@app.route("/apple-touch-icon-152x152-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-152x152.png", methods=["GET"])
@app.route("/apple-touch-icon-120x120-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-120x120.png", methods=["GET"])
@app.route("/apple-touch-icon-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon.png", methods=["GET"])
async def apple_touch_icon(request):
    return await file("app/static/icon_512.png", mime_type="image/png")


@app.route("/manifest.json")
async def manifest(request):
    return await file("app/static/manifest.json", mime_type="application/manifest+json")


@app.route("/service-worker.js")
async def service_worker(request):
    return await file("app/static/service-worker.js", mime_type="application/javascript")


@app.route("/health")
async def health_check(request):
    return {"status": "OK"}


####################################################################
# MARK: エラーハンドラー
####################################################################
@app.exception(404)
async def not_found(request, exception):
    return await common.not_found_page_view_async(request)


def main():
    """WSGIサーバー用のエントリーポイント

    Returns:
        Sanic: Sanicアプリケーションインスタンス
    """
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))