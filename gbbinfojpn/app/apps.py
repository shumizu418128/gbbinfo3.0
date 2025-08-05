import os

from django.apps import AppConfig
from django.conf import settings

from . import translation


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

        translation.initialize_translated_urls()

        # world_map削除
        if settings.DEBUG:
            templates_dir = os.path.join(
                settings.BASE_DIR, "gbbinfojpn", "app", "templates"
            )
            if os.path.exists(templates_dir):
                for year_dir in os.listdir(templates_dir):
                    year_path = os.path.join(templates_dir, year_dir)
                    if os.path.isdir(year_path):
                        world_map_path = os.path.join(year_path, "world_map")
                        if os.path.exists(world_map_path):
                            for file in os.listdir(world_map_path):
                                if file.endswith(".html"):
                                    file_path = os.path.join(world_map_path, file)
                                    os.remove(file_path)
