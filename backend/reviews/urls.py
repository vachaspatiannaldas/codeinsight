from django.urls import path

from .views import health_check, review_pr, get_review

urlpatterns = [
    path("health/", health_check),
    path("review/", review_pr),
    path("review/<uuid:review_id>/", get_review),
]