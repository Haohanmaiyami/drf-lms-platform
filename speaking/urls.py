from django.urls import path

from speaking.views import (
    LessonSpeakingAttemptListCreateAPIView,
    SpeakingAttemptCompleteUploadAPIView,
    SpeakingAttemptDetailAPIView,
)


app_name = "speaking"


urlpatterns = [
    path(
        (
            "lessons/"
            "<uuid:lesson_id>/"
            "speaking-attempts/"
        ),
        (
            LessonSpeakingAttemptListCreateAPIView
            .as_view()
        ),
        name=(
            "lesson-speaking-"
            "attempt-list-create"
        ),
    ),
    path(
        (
            "speaking-attempts/"
            "<uuid:attempt_id>/"
            "complete-upload/"
        ),
        (
            SpeakingAttemptCompleteUploadAPIView
            .as_view()
        ),
        name=(
            "speaking-attempt-"
            "complete-upload"
        ),
    ),
    path(
        (
            "speaking-attempts/"
            "<uuid:attempt_id>/"
        ),
        (
            SpeakingAttemptDetailAPIView
            .as_view()
        ),
        name="speaking-attempt-detail",
    ),
]