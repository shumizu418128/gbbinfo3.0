import logging
import os

from flask import (
    Flask,
    request,
    send_file,
)
from flask_babel import Babel, _
from flask_caching import Cache
from flask_sitemapper import Sitemapper

from app.config.config import (
    BASE_DIR,
    MINUTE,
    SUPPORTED_LOCALES,
)
from app.context_processors import (
    common_variables,
    get_locale,
    initialize_background_tasks,
)
from app.views import (
    beatboxer_finder,
    beatboxer_web_search,
    common,
    language,
    participant_detail,
    participants,
    result,
    rule,
    site_navigation,
    world_map,
)

# waitress.queue ロガーを無効化
_waitress_queue_logger = logging.getLogger("waitress.queue")
_waitress_queue_logger.propagate = False
_waitress_queue_logger.disabled = True

sitemapper = Sitemapper()

app = Flask(__name__)
sitemapper.init_app(app)


####################################################################
# MARK: 設定
####################################################################
class ProductionConfig:
    BABEL_DEFAULT_LOCALE = "ja"
    BABEL_SUPPORTED_LOCALES = SUPPORTED_LOCALES
    BABEL_DEFAULT_TIMEZONE = "Asia/Tokyo"
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "app" / "translations")
    CACHE_DEFAULT_TIMEOUT = 15 * MINUTE  # キャッシュの有効期限を15分に設定
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.getenv("REDIS_URL")
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    TEMPLATES_AUTO_RELOAD = False


class PRConfig(ProductionConfig):
    CACHE_REDIS_URL = os.getenv("REDIS_PR_URL")


class TestConfig(ProductionConfig):
    CACHE_TYPE = "null"
    DEBUG = True
    SECRET_KEY = "test"
    TEMPLATES_AUTO_RELOAD = True


# テスト環境ではキャッシュを無効化
# ローカル環境にはこの環境変数を設定してある
if os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp":
    print("\n")
    print("******************************************************************")
    print("*                                                                *")
    print("*    GBBINFO-JPN is running in test mode!                        *")
    print("*    Access the application at http://127.0.0.1:10000?lang=ja    *")
    print("*                                                                *")
    print("******************************************************************")
    app.config.from_object(TestConfig)
    IS_LOCAL = True
    IS_PULL_REQUEST = False
elif os.getenv("IS_PULL_REQUEST") == "true":
    app.config.from_object(PRConfig)
    IS_PULL_REQUEST = True
    IS_LOCAL = False
else:
    app.config.from_object(ProductionConfig)
    IS_PULL_REQUEST = False
    IS_LOCAL = False

try:
    flask_cache = Cache(app)
except Exception:
    print("************ WARNING: Redis connection failed ************", flush=True)
    app.config["CACHE_TYPE"] = "FileSystemCache"
    flask_cache = Cache(app)
babel = Babel(app)
test = _("test")  # テスト翻訳

# バックグラウンド初期化タスクはキャッシュ初期化後に起動
AVAILABLE_YEARS, OTHERS_CONTENT, YEARS_LIST, CONTENTS_PER_YEAR, TRAVEL_CONTENT = (
    initialize_background_tasks(IS_LOCAL)
)


####################################################################
# MARK: 共通変数
####################################################################
@app.before_request
def before_request():
    get_locale()


@app.context_processor
def set_common_variables():
    return common_variables(
        IS_LOCAL=IS_LOCAL,
        IS_PULL_REQUEST=IS_PULL_REQUEST,
    )


@babel.localeselector
def locale_selector():
    return get_locale()


#####################################################################
# URL
#####################################################################
# MARK: リダイレクト
@app.route("/")
def redirect_to_latest_top():
    return common.top_redirect_view()


@app.route("/2022/<string:content>")
def content_2022(content):
    return common.content_2022_view(content)


# MARK: deprecated
@app.route("/<int:year>/time_schedule")
def time_schedule(year):
    return common.time_schedule_view(year)


@app.route("/lang")
def change_language():
    return language.change_language()


@app.route("/others/participant_detail")
def participant_detail_deprecated():
    return participant_detail.participant_detail_deprecated_view()


# MARK: POST
@app.route("/beatboxer_tavily_search", methods=["POST"])
def beatboxer_tavily_search():
    return beatboxer_web_search.post_beatboxer_tavily_search()


@app.route("/search_suggestions", methods=["POST"])
def search_suggestion():
    return site_navigation.post_search_suggestion()


@app.route("/<int:year>/search", methods=["POST"])
def search(year):
    return site_navigation.post_search(
        year, IS_LOCAL=IS_LOCAL, IS_PULL_REQUEST=IS_PULL_REQUEST
    )


@app.route("/<int:year>/search_participants", methods=["POST"])
def search_participants(year):
    return beatboxer_finder.post_search_participants(year)


@app.route("/answer_translation", methods=["POST"])
def answer_translation():
    return beatboxer_web_search.post_answer_translation()


# MARK: 要データ取得
@sitemapper.include(url_variables={"year": AVAILABLE_YEARS})
@app.route("/<int:year>/world_map")
def world_map_view(year):
    return world_map.world_map_view(year)


@sitemapper.include(url_variables={"year": AVAILABLE_YEARS})
@app.route("/<int:year>/rule")
def rule_view(year):
    return rule.rules_view(year)


@sitemapper.include(url_variables={"year": AVAILABLE_YEARS})
@app.route("/<int:year>/participants")
def participants_view(year):
    return participants.participants_view(year)


@sitemapper.include(url_variables={"year": AVAILABLE_YEARS})
@app.route("/<int:year>/cancels")
def cancels_view(year):
    return participants.cancels_view(year)


@sitemapper.include(url_variables={"year": AVAILABLE_YEARS})
@app.route("/<int:year>/result")
def result_view(year):
    return result.result_view(year)


@sitemapper.include(url_variables={"year": AVAILABLE_YEARS})
@app.route("/<int:year>/japan")
def japan(year):
    return participants.participants_country_specific_view(year)


@sitemapper.include(url_variables={"year": AVAILABLE_YEARS})
@app.route("/<int:year>/korea")
def korea(year):
    return participants.participants_country_specific_view(year)


# @sitemapper.include()
@app.route("/participant_detail/<int:participant_id>/<string:mode>")
def participant_detail_view(participant_id, mode):
    return participant_detail.participant_detail_view(participant_id, mode)


@app.route("/notice")
def notice_view():
    return common.notice_view()


# MARK: 通常ページ
@sitemapper.include(url_variables={"content": OTHERS_CONTENT})
@app.route("/others/<string:content>")
def others(content):
    return common.other_content_view(content)


@sitemapper.include(url_variables={"content": TRAVEL_CONTENT})
@app.route("/travel/<string:content>")
def travel(content):
    return common.travel_content_view(content)


@sitemapper.include(url_variables={"year": YEARS_LIST, "content": CONTENTS_PER_YEAR})
@app.route("/<int:year>/<string:content>")
def common_content(year, content):
    return common.content_view(year, content)


####################################################################
# MARK: 静的ファイル
####################################################################
@app.route("/sitemap.xml")
def sitemap_xml():
    return sitemapper.generate()


@app.route("/.well-known/discord")
def discord():
    return send_file("static/discord")


@app.route("/robots.txt")
def robots_txt():
    return send_file("static/robots.txt", mimetype="text/plain")


@app.route("/ads.txt")
def ads_txt():
    return send_file("static/ads.txt", mimetype="text/plain")


@app.route("/naverc158f3394cb78ff00c17f0a687073317.html")
def naver_verification():
    return send_file("static/naverc158f3394cb78ff00c17f0a687073317.html")


@app.route("/favicon.ico", methods=["GET"])
def favicon_ico():
    return send_file("static/favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.route("/apple-touch-icon-152x152-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-152x152.png", methods=["GET"])
@app.route("/apple-touch-icon-120x120-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-120x120.png", methods=["GET"])
@app.route("/apple-touch-icon-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon.png", methods=["GET"])
def apple_touch_icon():
    return send_file("static/icon_512.png", mimetype="image/png")


@app.route("/manifest.json")
def manifest():
    return send_file("static/manifest.json", mimetype="application/manifest+json")


@app.route("/service-worker.js")
def service_worker():
    return send_file("static/service-worker.js", mimetype="application/javascript")


@app.route("/health")
def health_check():
    return os.getenv("RENDER_GIT_COMMIT", "-")[:7]


####################################################################
# MARK: エラーハンドラー
####################################################################
@app.errorhandler(404)
def not_found(error):
    print(f"404 Not Found: {request.path}", flush=True)
    return common.not_found_page_view()


@app.errorhandler(500)
def internal_server_error(error):
    print(f"500 Internal Server Error: {request.path}", flush=True)
    return common.internal_server_error_view()


def main():
    """WSGIサーバー用のエントリーポイント

    Returns:
        Flask: Flaskアプリケーションインスタンス
    """
    return app
