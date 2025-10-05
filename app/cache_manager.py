"""
キャッシュ管理モジュール

このモジュールはFlask-Cachingのキャッシュオブジェクトを管理し、
循環インポートを回避するために使用されます。
"""

from flask import Flask
from flask_caching import Cache


class CacheManager:
    """キャッシュマネージャークラス

    アプリケーション全体で使用されるキャッシュオブジェクトを管理します。
    """

    def __init__(self):
        self._cache = None
        self._app = None

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
                return self._cache.memoize(timeout)(func)(*args, **kwargs)

            return wrapper

        return decorator


# グローバルなキャッシュマネージャーインスタンス
cache_manager = CacheManager()
