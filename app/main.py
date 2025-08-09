import logging
import os
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    send_file,
)
from flask_babel import Babel, _
from flask_caching import Cache

from app.context_processors import (
    common_variables,
    get_locale,
    initialize_background_tasks,
    set_request_data,
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

# waitress.queue ロガーを無効化
_waitress_queue_logger = logging.getLogger("waitress.queue")
_waitress_queue_logger.propagate = False
_waitress_queue_logger.disabled = True

app = Flask(__name__)


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
    ("ta", "தமிழ்"),
    ("th", "ไทย"),
    ("zh_Hans_CN", "简体中文"),
    ("zh_Hant_TW", "繁體中文"),
]
BASE_DIR = Path(__file__).resolve().parent.parent
BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]
LAST_UPDATED = "UPDATE " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " JST"


class Config:
    BABEL_DEFAULT_LOCALE = "ja"
    BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "app" / "translations")
    CACHE_DEFAULT_TIMEOUT = 0
    CACHE_TYPE = "filesystem"
    CACHE_DIR = str(BASE_DIR / "cache")
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    TEMPLATES_AUTO_RELOAD = False


class TestConfig(Config):
    CACHE_DEFAULT_TIMEOUT = 0
    DEBUG = True
    SECRET_KEY = "test"
    TEMPLATES_AUTO_RELOAD = True


# テスト環境ではキャッシュを無効化
# ローカル環境にはこの環境変数を設定してある
if os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp":
    print("\n")
    print("******************************************************************")
    print("*                                                                *")
    print("*         GBBINFO-JPN is running in test mode!                   *")
    print("*         Access the application at http://127.0.0.1:10000       *")
    print("*                                                                *")
    print("******************************************************************")
    app.config.from_object(TestConfig)
    IS_LOCAL = True
    IS_PULL_REQUEST = False
else:
    app.config.from_object(Config)
    IS_LOCAL = False
    IS_PULL_REQUEST = os.getenv("IS_PULL_REQUEST") == "True"

flask_cache = Cache(app)
babel = Babel(app)
test = _("test")  # テスト翻訳

# バックグラウンド初期化タスクはキャッシュ初期化後に起動
initialize_background_tasks(BABEL_SUPPORTED_LOCALES)


####################################################################
# MARK: 共通変数
####################################################################
@app.before_request
def set_session_language():
    set_request_data(BABEL_SUPPORTED_LOCALES)


@app.context_processor
def set_common_variables():
    return common_variables(
        BABEL_SUPPORTED_LOCALES=BABEL_SUPPORTED_LOCALES,
        LANGUAGES=LANGUAGES,
        IS_LOCAL=IS_LOCAL,
        IS_PULL_REQUEST=IS_PULL_REQUEST,
        LAST_UPDATED=LAST_UPDATED,
    )


@babel.localeselector
def locale_selector():
    return get_locale(BABEL_SUPPORTED_LOCALES)


#####################################################################
# MARK: URL
#####################################################################
# リダイレクト
app.add_url_rule("/", "redirect_to_latest_top", common.top_redirect_view)
app.add_url_rule(
    "/lang",
    "change_language",
    language.change_language,
    defaults={"BABEL_SUPPORTED_LOCALES": BABEL_SUPPORTED_LOCALES},
)
app.add_url_rule("/2022/<string:content>", "2022_content", common.content_2022_view)

# POSTリクエスト
app.add_url_rule(
    "/beatboxer_tavily_search",
    "beatboxer_tavily_search",
    beatboxer_tavily_search.post_beatboxer_tavily_search,
    methods=["POST"],
)
app.add_url_rule(
    "/search_suggestions",
    "search_suggestion",
    gemini_search.post_gemini_search_suggestion,
    methods=["POST"],
)
app.add_url_rule(
    "/<int:year>/search",
    "search",
    gemini_search.post_gemini_search,
    defaults={"IS_LOCAL": IS_LOCAL, "IS_PULL_REQUEST": IS_PULL_REQUEST},
    methods=["POST"],
)
app.add_url_rule(
    "/<int:year>/search_participants",
    "search_participants",
    search_participants.post_search_participants,
    methods=["POST"],
)

# 要データ取得
app.add_url_rule("/<int:year>/world_map", "world_map", world_map.world_map_view)
app.add_url_rule("/<int:year>/rule", "rule", rule.rules_view)
app.add_url_rule(
    "/<int:year>/participants", "participants", participants.participants_view
)
app.add_url_rule("/<int:year>/result", "result", result.result_view)
app.add_url_rule(
    "/<int:year>/japan", "japan", participants.participants_country_specific_view
)
app.add_url_rule(
    "/<int:year>/korea", "korea", participants.participants_country_specific_view
)
app.add_url_rule(
    "/others/participant_detail",
    "participant_detail",
    participant_detail.participant_detail_view,
)

# その他通常ページ
app.add_url_rule("/others/<string:content>", "others", common.other_content_view)
app.add_url_rule("/<int:year>/<string:content>", "common", common.content_view)


####################################################################
# MARK: 静的ファイル
####################################################################
@app.route("/.well-known/discord")
def discord():
    return send_file(".well-known/discord")


@app.route("/sitemap.xml")
def sitemap():
    return send_file("static/sitemap.xml", mimetype="application/xml")


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
    return "OK"


####################################################################
# MARK: エラーハンドラー
####################################################################
@app.errorhandler(404)
def not_found(error):
    return common.not_found_page_view()


def main():
    """WSGIサーバー用のエントリーポイント

    Returns:
        Flask: Flaskアプリケーションインスタンス
    """
    return app
