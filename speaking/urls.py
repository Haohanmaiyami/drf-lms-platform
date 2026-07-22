from django.urls import path

from speaking.views import (
    LessonSpeakingAttemptListCreateAPIView,
    SpeakingAttemptDetailAPIView,
)


app_name = "speaking"

# 1) какие 2) детали и метрики

urlpatterns = [
    path(
        "lessons/<uuid:lesson_id>/speaking-attempts/",
        LessonSpeakingAttemptListCreateAPIView.as_view(),
        name="lesson-speaking-attempt-list-create",
    ),
    path(
        "speaking-attempts/<uuid:attempt_id>/",
        SpeakingAttemptDetailAPIView.as_view(),
        name="speaking-attempt-detail",
    ),
]