from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # apps/ 配下に置いているのでドット区切りのフルパスで指定する
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "アカウント"
