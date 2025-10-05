"""
キャッシュ統計情報表示ビュー

キャッシュヒット率やミス率などの統計情報を表示するエンドポイントを提供します。
"""

from flask import Blueprint, jsonify

from app.cache_manager import cache_manager

# ブループリントを作成
cache_stats_bp = Blueprint("cache_stats", __name__)


@cache_stats_bp.route("/api/cache-stats")
def api_cache_stats():
    """キャッシュ統計情報をJSON形式で返します。

    Returns:
        dict: キャッシュ統計情報のJSONレスポンス
    """
    # 詳細な統計情報を取得
    detailed_stats = cache_manager.get_detailed_cache_stats()
    return jsonify({"data": detailed_stats})


@cache_stats_bp.route("/api/cache-stats/reset", methods=["POST"])
def reset_cache_stats():
    """キャッシュ統計情報をリセットします。

    Returns:
        dict: リセット結果のJSONレスポンス
    """
    cache_manager.reset_cache_stats()
    return jsonify(
        {"message": "キャッシュ統計情報をリセットしました。"}
    )
