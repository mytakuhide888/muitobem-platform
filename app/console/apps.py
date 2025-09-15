from django.apps import AppConfig

class ConsoleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.console"     # ← フルパスに更新
    label = "console"        # （任意）DBラベル固定したい場合
