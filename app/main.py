import os
import warnings

from dotenv import load_dotenv
from flask import (
    Flask,
    g,
    request,
    send_file,
    session,
)
from flask_babel import Babel, _
from flask_caching import Cache
from flask_sitemapper import Sitemapper

from app import settings
from app.context_processors import common_variables, get_locale
from app.settings import Config, TestConfig

# Import all view modules
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

app = Flask(__name__)
sitemapper = Sitemapper()
sitemapper.init_app(app)
cache = Cache(app)
babel = Babel(app)
test = _("test")  # テスト翻訳

# 特定の警告を無視
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Flask-Caching: CACHE_TYPE is set to null, caching is effectively disabled.",
)
# テスト環境ではキャッシュを無効化
# ローカル環境にはこの環境変数を設定してある
if os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp":
    print("\n")
    print("******************************************************************")
    print("*                                                                *")
    print("*         GBBINFO-JPN is running in test mode!                   *")
    print("*         Access the application at http://127.0.0.1:8080        *")
    print("*                                                                *")
    print("******************************************************************")
    load_dotenv()
    app.config.from_object(TestConfig)
else:
    app.config.from_object(Config)
    IS_LOCAL = False
    IS_PULL_REQUEST = os.getenv("IS_PULL_REQUEST") == "True"


####################################################################
# MARK: 共通変数
####################################################################
@app.before_request
def set_request_data():
    """
    リクエストごとに実行される関数。
    URLを取得して、グローバル変数に保存します。
    これにより、リクエストのURLをグローバルにアクセスできるようにします。
    また、セッションに言語が設定されていない場合、デフォルトの言語を設定します。

    Returns:
        None
    """
    g.current_url = request.path

    if "X-Forwarded-For" in request.headers:
        user_ip = request.headers["X-Forwarded-For"].split(",")[0].strip()
        print(f"IPアドレス: {user_ip}", flush=True)

    # 初回アクセス時の言語設定
    if "language" not in session:
        best_match = request.accept_languages.best_match(
            settings.BABEL_SUPPORTED_LOCALES
        )
        session["language"] = best_match if best_match else "ja"


@app.context_processor
def set_common_variables():
    return common_variables()


@babel.localeselector
def locale_selector():
    return get_locale()


#####################################################################
# MARK: URL
#####################################################################
# リダイレクト
app.add_url_rule("/", "redirect_to_latest_top", common.top_redirect_view)
app.add_url_rule("/lang", "change_language", language.change_language)
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
    "/<int:year>/search", "search", gemini_search.post_gemini_search, methods=["POST"]
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
@cache.cached()
def sitemap():
    return sitemapper.generate()


@app.route("/robots.txt")
def robots_txt():
    return send_file("robots.txt", mimetype="text/plain")


@app.route("/ads.txt")
def ads_txt():
    return send_file("ads.txt", mimetype="text/plain")


@app.route("/naverc158f3394cb78ff00c17f0a687073317.html")
def naver_verification():
    return send_file("naverc158f3394cb78ff00c17f0a687073317.html")


@app.route("/favicon.ico", methods=["GET"])
def favicon_ico():
    return send_file("favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.route("/apple-touch-icon-152x152-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-152x152.png", methods=["GET"])
@app.route("/apple-touch-icon-120x120-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon-120x120.png", methods=["GET"])
@app.route("/apple-touch-icon-precomposed.png", methods=["GET"])
@app.route("/apple-touch-icon.png", methods=["GET"])
def apple_touch_icon():
    return send_file("icon_512.png", mimetype="image/png")


@app.route("/manifest.json")
def manifest():
    return send_file("manifest.json", mimetype="application/manifest+json")


@app.route("/service-worker.js")
def service_worker():
    return send_file("service-worker.js", mimetype="application/javascript")


@app.route("/health")
def health_check():
    return "OK"


####################################################################
# MARK: エラーハンドラー
####################################################################
@app.errorhandler(404)
def not_found(error):
    return common.not_found_page_view()
