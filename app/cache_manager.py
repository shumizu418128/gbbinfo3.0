"""
キャッシュ管理モジュール

このモジュールはFlask-Cachingのキャッシュオブジェクトを管理し、
循環インポートを回避するために使用されます。
"""

import hashlib
import threading
from collections import defaultdict
from datetime import datetime

from flask import Flask
from flask_caching import Cache


class CacheStats:
    """キャッシュ統計情報を管理するクラス

    キャッシュヒット率やミス率などの統計情報を追跡します。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._total_requests = 0
        # 関数別の統計情報
        self._function_stats = defaultdict(lambda: {"hits": 0, "misses": 0, "total": 0})
        # キャッシュキー別の統計情報
        self._key_stats = defaultdict(lambda: {"hits": 0, "misses": 0, "total": 0})
        # 統計記録開始時間
        self._start_time = datetime.now()

    def record_hit(self, function_name: str = None, cache_key: str = None):
        """キャッシュヒットを記録します。

        Args:
            function_name: 関数名（オプション）
            cache_key: キャッシュキー（オプション）
        """
        with self._lock:
            self._hits += 1
            self._total_requests += 1

            if function_name:
                self._function_stats[function_name]["hits"] += 1
                self._function_stats[function_name]["total"] += 1

            if cache_key:
                self._key_stats[cache_key]["hits"] += 1
                self._key_stats[cache_key]["total"] += 1

    def record_miss(self, function_name: str = None, cache_key: str = None):
        """キャッシュミスを記録します。

        Args:
            function_name: 関数名（オプション）
            cache_key: キャッシュキー（オプション）
        """
        with self._lock:
            self._misses += 1
            self._total_requests += 1

            if function_name:
                self._function_stats[function_name]["misses"] += 1
                self._function_stats[function_name]["total"] += 1

            if cache_key:
                self._key_stats[cache_key]["misses"] += 1
                self._key_stats[cache_key]["total"] += 1

    def get_stats(self):
        """統計情報を取得します。

        Returns:
            dict: 統計情報の辞書
                - hits: ヒット数
                - misses: ミス数
                - total_requests: 総リクエスト数
                - hit_rate: ヒット率（0.0-1.0）
                - miss_rate: ミス率（0.0-1.0）
                - start_time: 統計記録開始時間
                - uptime_seconds: 稼働時間（秒）
        """
        with self._lock:
            hit_rate = (
                self._hits / self._total_requests if self._total_requests > 0 else 0.0
            )
            miss_rate = (
                self._misses / self._total_requests if self._total_requests > 0 else 0.0
            )
            uptime = (datetime.now() - self._start_time).total_seconds()

            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": self._total_requests,
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
                "start_time": self._start_time.isoformat(),
                "uptime_seconds": uptime,
            }

    def get_detailed_stats(self):
        """詳細な統計情報を取得します。

        Returns:
            dict: 詳細な統計情報の辞書
                - overall: 全体の統計情報
                - function_stats: 関数別の統計情報
                - key_stats: キャッシュキー別の統計情報
                - top_miss_functions: ミス率の高い関数トップ10
                - top_miss_keys: ミス率の高いキャッシュキートップ10
        """
        with self._lock:
            overall_stats = self.get_stats()

            # 関数別統計の計算
            function_stats = {}
            for func_name, stats in self._function_stats.items():
                total = stats["total"]
                if total > 0:
                    function_stats[func_name] = {
                        "hits": stats["hits"],
                        "misses": stats["misses"],
                        "total": total,
                        "hit_rate": stats["hits"] / total,
                        "miss_rate": stats["misses"] / total,
                    }

            # キャッシュキー別統計の計算
            key_stats = {}
            for key, stats in self._key_stats.items():
                total = stats["total"]
                if total > 0:
                    key_stats[key] = {
                        "hits": stats["hits"],
                        "misses": stats["misses"],
                        "total": total,
                        "hit_rate": stats["hits"] / total,
                        "miss_rate": stats["misses"] / total,
                    }

            # ミス率の高い関数トップ10
            top_miss_functions = sorted(
                function_stats.items(), key=lambda x: x[1]["miss_rate"], reverse=True
            )[:10]

            # ミス率の高いキャッシュキートップ10
            top_miss_keys = sorted(
                key_stats.items(), key=lambda x: x[1]["miss_rate"], reverse=True
            )[:10]

            return {
                "overall": overall_stats,
                "function_stats": function_stats,
                "key_stats": key_stats,
                "top_miss_functions": top_miss_functions,
                "top_miss_keys": top_miss_keys,
            }

    def reset_stats(self):
        """統計情報をリセットします。"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._total_requests = 0
            self._function_stats.clear()
            self._key_stats.clear()
            self._start_time = datetime.now()


class CacheManager:
    """キャッシュマネージャークラス

    アプリケーション全体で使用されるキャッシュオブジェクトを管理します。
    """

    def __init__(self):
        self._cache = None
        self._app = None
        self._stats = CacheStats()

    def init_app(self, app: Flask) -> None:
        """Flaskアプリケーションにキャッシュを初期化します。

        Args:
            app (Flask): Flaskアプリケーションインスタンス
        """
        self._app = app
        self._cache = Cache(app)

    @property
    def cache(self) -> Cache:
        """キャッシュオブジェクトを取得します。

        Returns:
            Cache: Flask-Cachingのキャッシュオブジェクト
        """
        if self._cache is None and self._app is not None:
            # 遅延初期化：アプリが設定されている場合は自動で初期化
            self._cache = Cache(self._app)
        return self._cache

    def memoize(self, timeout=None):
        """memoizeデコレータを提供します。

        Args:
            timeout: キャッシュのタイムアウト時間

        Returns:
            memoizeデコレータ
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # キャッシュが初期化されていない場合は通常の関数として実行
                if self._cache is None:
                    return func(*args, **kwargs)

                # キャッシュキーを生成
                key_payload = str(args) + str(sorted(kwargs.items()))
                key_hash = hashlib.md5(key_payload.encode("utf-8")).hexdigest()
                cache_key = f"{func.__name__}:{key_hash}"

                # キャッシュから取得を試行
                cached_result = self._cache.get(cache_key)
                if cached_result is not None:
                    # キャッシュヒット
                    self.record_cache_hit(
                        function_name=func.__name__, cache_key=cache_key
                    )
                    return cached_result
                else:
                    # キャッシュミス
                    self.record_cache_miss(
                        function_name=func.__name__, cache_key=cache_key
                    )
                    result = func(*args, **kwargs)
                    self._cache.set(cache_key, result, timeout=timeout)
                    return result

            return wrapper

        return decorator

    def get_cache_stats(self):
        """キャッシュ統計情報を取得します。

        Returns:
            dict: 統計情報の辞書
        """
        return self._stats.get_stats()

    def get_detailed_cache_stats(self):
        """詳細なキャッシュ統計情報を取得します。

        Returns:
            dict: 詳細な統計情報の辞書
        """
        return self._stats.get_detailed_stats()

    def reset_cache_stats(self):
        """キャッシュ統計情報をリセットします。"""
        self._stats.reset_stats()

    def record_cache_hit(self, function_name: str = None, cache_key: str = None):
        """キャッシュヒットを記録します。

        Args:
            function_name: 関数名（オプション）
            cache_key: キャッシュキー（オプション）
        """
        self._stats.record_hit(function_name, cache_key)

    def record_cache_miss(self, function_name: str = None, cache_key: str = None):
        """キャッシュミスを記録します。

        Args:
            function_name: 関数名（オプション）
            cache_key: キャッシュキー（オプション）
        """
        self._stats.record_miss(function_name, cache_key)


# グローバルなキャッシュマネージャーインスタンス
cache_manager = CacheManager()
