"""
キャッシュ管理モジュール

このモジュールはFlask-Cachingのキャッシュオブジェクトを管理し、
循環インポートを回避するために使用されます。
"""

import threading

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

    def record_hit(self):
        """キャッシュヒットを記録します。"""
        with self._lock:
            self._hits += 1
            self._total_requests += 1

    def record_miss(self):
        """キャッシュミスを記録します。"""
        with self._lock:
            self._misses += 1
            self._total_requests += 1

    def get_stats(self):
        """統計情報を取得します。

        Returns:
            dict: 統計情報の辞書
                - hits: ヒット数
                - misses: ミス数
                - total_requests: 総リクエスト数
                - hit_rate: ヒット率（0.0-1.0）
                - miss_rate: ミス率（0.0-1.0）
        """
        with self._lock:
            hit_rate = (
                self._hits / self._total_requests if self._total_requests > 0 else 0.0
            )
            miss_rate = (
                self._misses / self._total_requests if self._total_requests > 0 else 0.0
            )

            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": self._total_requests,
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
            }

    def reset_stats(self):
        """統計情報をリセットします。"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._total_requests = 0


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
                cache_key = (
                    f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                )

                # キャッシュから取得を試行
                cached_result = self._cache.get(cache_key)
                if cached_result is not None:
                    # キャッシュヒット
                    self.record_cache_hit()
                    return cached_result
                else:
                    # キャッシュミス
                    self.record_cache_miss()
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

    def reset_cache_stats(self):
        """キャッシュ統計情報をリセットします。"""
        self._stats.reset_stats()

    def record_cache_hit(self):
        """キャッシュヒットを記録します。"""
        self._stats.record_hit()

    def record_cache_miss(self):
        """キャッシュミスを記録します。"""
        self._stats.record_miss()


# グローバルなキャッシュマネージャーインスタンス
cache_manager = CacheManager()
