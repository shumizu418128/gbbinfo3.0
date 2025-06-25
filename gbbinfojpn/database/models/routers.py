"""
データベースルーター
SQLiteとSupabaseの使い分けを制御
"""


class DatabaseRouter:
    """
    データベースルーティング設定
    - SQLite: 管理画面用（User, Session, Admin関連）
    - Supabase: ウェブアプリケーションデータ用
    """

    def db_for_read(self, model, **hints):
        """読み取り操作のデータベースを決定"""
        # Django管理機能関連はSQLite
        if model._meta.app_label in ['auth', 'admin', 'sessions', 'contenttypes']:
            return 'default'

        # databaseアプリのモデルはSupabase
        if model._meta.app_label == 'database':
            return 'supabase'

        return None

    def db_for_write(self, model, **hints):
        """書き込み操作のデータベースを決定"""
        # Django管理機能関連はSQLite
        if model._meta.app_label in ['auth', 'admin', 'sessions', 'contenttypes']:
            return 'default'

        # databaseアプリのモデルはSupabase
        if model._meta.app_label == 'database':
            return 'supabase'

        return None

    def allow_relation(self, obj1, obj2, **hints):
        """関連の許可を決定"""
        db_set = {'default', 'supabase'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """マイグレーションの許可を決定"""
        # Django管理機能関連はdefault(SQLite)にのみマイグレート
        if app_label in ['auth', 'admin', 'sessions', 'contenttypes']:
            return db == 'default'

        # databaseアプリはsupabaseにのみマイグレート
        if app_label == 'database':
            return db == 'supabase'

        return None
