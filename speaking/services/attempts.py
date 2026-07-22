from django.db import transaction
from django.db.models import Max

from courses.models import Lesson
from speaking.models import SpeakingAttempt


@transaction.atomic
def create_speaking_attempt(
    *,
    user,
    lesson: Lesson,
) -> SpeakingAttempt:
    """
    Создаёт следующую попытку пользователя.

    Блокировка Lesson защищает от ситуации,
    когда два одновременных запроса получают
    одинаковый attempt_number.
    """

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
            value=Max("attempt_number"),
        )["value"]
        or 0
    )

    return SpeakingAttempt.objects.create(
        user=user,
        lesson=locked_lesson,
        attempt_number=last_number + 1,
    )