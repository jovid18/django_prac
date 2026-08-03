from django.contrib import admin

from .models import Favorite, Library


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ("name", "ward", "smoking_status", "latitude", "longitude", "data_source")
    list_filter = ("ward", "smoking_status", "data_source")
    search_fields = ("name", "address")
    ordering = ("ward", "name")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "library", "created_at")
    search_fields = ("user__email", "library__name")
