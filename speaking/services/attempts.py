from django.db import transaction
from django.db.models import Max

from courses.models import Lesson
from speaking.models import SpeakingAttempt
from speaking.services.storage import (
    build_audio_key,
)


@transaction.atomic
def create_speaking_attempt(
    *,
    user,
    lesson: Lesson,
    audio_content_type: str = "",
    file_extension: str = "",
) -> SpeakingAttempt:
    """Создаёт следующую попытку пользователя."""

    locked_lesson = (
        Lesson.objects
        .select_for_update()
        .get(pk=lesson.pk)
    )

    last_number = (
        SpeakingAttempt.objects
        .filter(
            user=user,
            lesson=locked_lesson,
        )
        .aggregate(
            value=Max(
                "attempt_number"
            ),
        )["value"]
        or 0
    )

    attempt = SpeakingAttempt(
        user=user,
        lesson=locked_lesson,
        attempt_number=(
            last_number + 1
        ),
        audio_content_type=(
            audio_content_type
        ),
    )

    if file_extension:
        attempt.audio_key = (
            build_audio_key(
                lesson_public_id=(
                    locked_lesson.public_id
                ),
                attempt_public_id=(
                    attempt.public_id
                ),
                file_extension=(
                    file_extension
                ),
            )
        )

    attempt.save()

    return attempt