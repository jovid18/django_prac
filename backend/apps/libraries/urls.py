from rest_framework.routers import DefaultRouter

from .views import LibraryViewSet

router = DefaultRouter()
router.register("libraries", LibraryViewSet, basename="library")

urlpatterns = router.urls
