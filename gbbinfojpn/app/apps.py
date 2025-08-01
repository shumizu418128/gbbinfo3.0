from django.apps import AppConfig


class GbbinfoJpnAppConfig(AppConfig):
    """
    GbbinfoJpnアプリケーションの設定クラス。

    このクラスはDjangoアプリケーションの設定を管理し、アプリケーションの初期化時に
    必要な初期化処理（例：翻訳済みURLの初期化）を行います。

    Attributes:
        default_auto_field (str): モデルのデフォルトの自動フィールド型。
        name (str): アプリケーションのPythonパス。
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "gbbinfojpn.app"

    def ready(self):
        """
        アプリケーションの初期化時に呼び出されるメソッド。

        このメソッドは、翻訳済みURLの初期化処理を行います。

        Raises:
            ImportError: translationモジュールのインポートに失敗した場合
        """
        from . import translation

        translation.initialize_translated_urls()
