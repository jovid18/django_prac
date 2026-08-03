from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import SocialAccount, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "display_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("プロフィール", {"fields": ("display_name",)}),
        (
            "権限",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("日時", {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("date_joined", "last_login")
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_uid", "created_at")
    list_filter = ("provider",)
    search_fields = ("user__email", "provider_uid")
