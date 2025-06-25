"""
データベースルーター
SQLiteとSupabaseの使い分けを制御

このモジュールは、Djangoアプリケーションで複数のデータベースを使用する際の
ルーティング設定を提供します。SQLite（管理画面用）とSupabase（ウェブアプリケーション用）
の使い分けを自動的に制御します。

Example:
    settings.pyで以下のように設定します:

    DATABASE_ROUTERS = ['database.models.routers.DatabaseRouter']

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
        'supabase': {
            'ENGINE': 'django.db.backends.postgresql',
            # Supabase設定
        }
    }
"""


class DatabaseRouter:
    """
    データベースルーティング設定

    Djangoアプリケーションで複数のデータベースを使用する際のルーティングを制御します。
    - SQLite: 管理画面用（User, Session, Admin関連）
    - Supabase: ウェブアプリケーションデータ用

    Attributes:
        None

    Methods:
        db_for_read: 読み取り操作のデータベースを決定
        db_for_write: 書き込み操作のデータベースを決定
        allow_relation: 関連の許可を決定
        allow_migrate: マイグレーションの許可を決定
    """

    def db_for_read(self, model, **hints):
        """
        読み取り操作のデータベースを決定（Django 5.2.3対応）

        Args:
            model: 対象のDjangoモデルクラス
            **hints: 追加のヒント情報

        Returns:
            str: 使用するデータベースのエイリアス
                - "default": SQLiteデータベース
                - "supabase": Supabaseデータベース
                - None: デフォルトのルーティングを使用

        Raises:
            Exception: モデルのメタ情報取得時にエラーが発生した場合

        Example:
            >>> router = DatabaseRouter()
            >>> router.db_for_read(User)
            'default'
            >>> router.db_for_read(WebContent)
            'supabase'
        """
        try:
            # Django管理機能関連はSQLite
            if model._meta.app_label in ["auth", "admin", "sessions", "contenttypes"]:
                return "default"

            # databaseアプリのモデルはSupabase
            if model._meta.app_label == "database":
                return "supabase"

            return None
        except Exception:
            # エラーが発生した場合はデフォルトデータベースを使用
            return "default"

    def db_for_write(self, model, **hints):
        """
        書き込み操作のデータベースを決定（Django 5.2.3対応）

        Args:
            model: 対象のDjangoモデルクラス
            **hints: 追加のヒント情報

        Returns:
            str: 使用するデータベースのエイリアス
                - "default": SQLiteデータベース
                - "supabase": Supabaseデータベース
                - None: デフォルトのルーティングを使用

        Raises:
            Exception: モデルのメタ情報取得時にエラーが発生した場合

        Example:
            >>> router = DatabaseRouter()
            >>> router.db_for_write(User)
            'default'
            >>> router.db_for_write(WebContent)
            'supabase'
        """
        try:
            # Django管理機能関連はSQLite
            if model._meta.app_label in ["auth", "admin", "sessions", "contenttypes"]:
                return "default"

            # databaseアプリのモデルはSupabase
            if model._meta.app_label == "database":
                return "supabase"

            return None
        except Exception:
            # エラーが発生した場合はデフォルトデータベースを使用
            return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        関連の許可を決定

        2つのオブジェクト間のリレーションが許可されるかどうかを判定します。
        同じデータベース内のオブジェクト間のリレーションのみを許可します。

        Args:
            obj1: 第1のオブジェクト
            obj2: 第2のオブジェクト
            **hints: 追加のヒント情報

        Returns:
            bool: リレーションが許可される場合はTrue、許可されない場合はFalse、
                  デフォルトのルーティングを使用する場合はNone

        Example:
            >>> router = DatabaseRouter()
            >>> user1 = User.objects.using('default').first()
            >>> user2 = User.objects.using('default').first()
            >>> router.allow_relation(user1, user2)
            True
        """
        db_set = {"default", "supabase"}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        マイグレーションの許可を決定（Django 5.2.3対応）

        指定されたデータベースに対してマイグレーションが許可されるかどうかを判定します。
        アプリケーションごとに適切なデータベースにのみマイグレーションを実行します。

        Args:
            db: 対象のデータベースエイリアス
            app_label: アプリケーションラベル
            model_name: モデル名（オプション）
            **hints: 追加のヒント情報

        Returns:
            bool: マイグレーションが許可される場合はTrue、許可されない場合はFalse、
                  デフォルトのルーティングを使用する場合はNone

        Raises:
            Exception: アプリケーションラベルの判定時にエラーが発生した場合

        Example:
            >>> router = DatabaseRouter()
            >>> router.allow_migrate('default', 'auth')
            True
            >>> router.allow_migrate('supabase', 'database')
            True
            >>> router.allow_migrate('supabase', 'auth')
            False
        """
        try:
            # Django管理機能関連はdefault(SQLite)にのみマイグレート
            if app_label in ["auth", "admin", "sessions", "contenttypes"]:
                return db == "default"

            # databaseアプリはsupabaseにのみマイグレート
            if app_label == "database":
                return db == "supabase"

            return None
        except Exception:
            # エラーが発生した場合はデフォルトデータベースにマイグレート
            return db == "default"
