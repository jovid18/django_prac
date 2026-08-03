"""ユーザーとソーシャル連携。

設計の意図は docs/04-data-model.md を参照。要点だけ再掲する:

- username を捨てて email を USERNAME_FIELD にする
  （Google ログイン時に埋めようのない username が邪魔になるため）
- ソーシャル連携は User のカラムにせず SocialAccount に分ける
  （プロバイダが増えてもスキーマが変わらない）
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("メールアドレスは必須です。")
        user = self.model(email=self.normalize_email(email), **extra)
        if password:
            user.set_password(password)
        else:
            # ソーシャルログインのみのユーザーはパスワードを持たない
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("is_staff=True である必要があります。")
        if extra.get("is_superuser") is not True:
            raise ValueError("is_superuser=True である必要があります。")
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("メールアドレス", unique=True)
    display_name = models.CharField("表示名", max_length=50, blank=True)
    is_active = models.BooleanField("有効", default=True)
    is_staff = models.BooleanField("スタッフ", default=False)
    date_joined = models.DateTimeField("登録日時", auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.email


class SocialAccount(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        # LINE = "line", "LINE"  # スコープ外。追加するならここ（docs/01-overview.md）

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField("プロバイダ", max_length=20, choices=Provider.choices)
    # Google の sub。メールアドレスは変わりうるが sub は不変なので、
    # こちらを本人特定のキーにする（docs/06-auth.md）。
    provider_uid = models.CharField("プロバイダ側 ID", max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ソーシャル連携"
        verbose_name_plural = "ソーシャル連携"
        constraints = [
            models.UniqueConstraint(fields=["provider", "provider_uid"], name="uniq_provider_uid")
        ]

    def __str__(self):
        return f"{self.get_provider_display()}:{self.user.email}"
