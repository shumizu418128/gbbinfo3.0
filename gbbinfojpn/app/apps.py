from django.apps import AppConfig


class GbbinfoJpnAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gbbinfojpn.app"

    def ready(self):
        from . import translation

        translation.initialize_translated_urls()
