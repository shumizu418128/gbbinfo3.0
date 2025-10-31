import logging
import os
from datetime import datetime, timedelta, timezone
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
    ("be", "Беларуская"),
    ("da", "Dansk"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("et", "Eesti"),
    ("fr", "Français"),
    ("ga", "Gaeilge"),
    ("hi", "हिन्दी"),
    ("hu", "Magyar"),
    ("it", "Italiano"),
    ("ms", "Bahasa MY"),
    ("no", "Norsk"),
    ("pl", "Polski"),
    ("pt", "Português"),
    ("ta", "தமிழ்"),
    ("zh_Hans_CN", "简体中文"),
    ("zh_Hant_TW", "繁體中文"),
]
BASE_DIR = Path(__file__).resolve().parent.parent
BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]
LAST_UPDATED = datetime.now(timezone(timedelta(hours=9)))
MINUTE = 60


class Config:
    BABEL_DEFAULT_LOCALE = "ja"
    BABEL_SUPPORTED_LOCALES = [code for code, _ in LANGUAGES]
    BABEL_DEFAULT_TIMEZONE = "Asia/Tokyo"
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "app" / "translations")
    CACHE_DEFAULT_TIMEOUT = 60 * MINUTE  # キャッシュの有効期限を60分に設定
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.getenv("REDIS_URL")
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    TEMPLATES_AUTO_RELOAD = False


class PRConfig(Config):
    CACHE_REDIS_URL = os.getenv("REDIS_PR_URL")


class TestConfig(Config):
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
    app.config.from_object(Config)
    IS_PULL_REQUEST = False
    IS_LOCAL = False

flask_cache = Cache(app)
babel = Babel(app)
test = _("test")  # テスト翻訳

# バックグラウンド初期化タスクはキャッシュ初期化後に起動
initialize_background_tasks(IS_LOCAL)


####################################################################
# MARK: 共通変数
####################################################################
@app.before_request
def before_request():
    get_locale(BABEL_SUPPORTED_LOCALES)


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
app.add_url_rule(
    "/answer_translation",
    "answer_translation",
    beatboxer_tavily_search.post_answer_translation,
    methods=["POST"],
)

# 要データ取得
app.add_url_rule("/<int:year>/world_map", "world_map", world_map.world_map_view)
app.add_url_rule("/<int:year>/rule", "rule", rule.rules_view)
app.add_url_rule(
    "/<int:year>/participants", "participants", participants.participants_view
)
app.add_url_rule("/<int:year>/cancels", "cancels", participants.cancels_view)
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
    return send_file("static/discord")


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
    return os.getenv("RENDER_GIT_COMMIT", "-")[:7]


####################################################################
# MARK: エラーハンドラー
####################################################################
@app.errorhandler(404)
def not_found(error):
    return common.not_found_page_view()


@app.errorhandler(500)
def internal_server_error(error):
    return common.internal_server_error_view()


def main():
    """WSGIサーバー用のエントリーポイント

    Returns:
        Flask: Flaskアプリケーションインスタンス
    """
    return app
