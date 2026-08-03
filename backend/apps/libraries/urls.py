from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FavoriteListView, LibraryViewSet

router = DefaultRouter()
router.register("libraries", LibraryViewSet, basename="library")

# `/api/favorites/` はルータの外に置く。
# Favorite を単体で CRUD させるつもりが無い（登録・解除は
# `/api/libraries/{id}/favorite/` 側）ので、ViewSet を生やすと
# 使わない detail / update / destroy まで公開されてしまう。
urlpatterns = [
    *router.urls,
    path("favorites/", FavoriteListView.as_view(), name="favorite-list"),
]
