from datetime import timedelta

from django.db.models import (
    Avg,
    Count,
    Sum,
)
from django.db.models.functions import (
    TruncDate,
)
from django.utils import timezone

from courses.models import Lesson
from speaking.models import (
    SpeakingAttempt,
)


LEVEL_ORDER = [
    Lesson.Level.BEGINNER,
    Lesson.Level.INTERMEDIATE,
    Lesson.Level.UPPER_INTERMEDIATE,
]


def calculate_streak(
    active_days,
):
    """
    Считает последовательные активные дни.

    Если пользователь ещё не занимался
    сегодня, streak может начинаться вчера.
    """

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    if today in active_days:
        current_day = today
    elif yesterday in active_days:
        current_day = yesterday
    else:
        return 0

    streak = 0

    while current_day in active_days:
        streak += 1
        current_day -= timedelta(days=1)

    return streak


def build_level_progress(
    user,
):
    """
    Считает прогресс по speaking-урокам
    текущего уровня.
    """

    totals_rows = (
        Lesson.objects
        .filter(
            speaking_config__isnull=False,
            level__in=LEVEL_ORDER,
        )
        .values("level")
        .annotate(
            total=Count("id"),
        )
    )

    totals = {
        row["level"]: row["total"]
        for row in totals_rows
    }

    completed_rows = (
        SpeakingAttempt.objects
        .filter(
            user=user,
            status=(
                SpeakingAttempt
                .Status.COMPLETED
            ),
            lesson__level__in=LEVEL_ORDER,
        )
        .values("lesson__level")
        .annotate(
            completed=Count(
                "lesson_id",
                distinct=True,
            ),
        )
    )

    completed = {
        row["lesson__level"]: (
            row["completed"]
        )
        for row in completed_rows
    }

    available_levels = [
        level
        for level in LEVEL_ORDER
        if totals.get(level, 0) > 0
    ]

    if not available_levels:
        return {
            "current_level": None,
            "next_level": None,
            "completed_lessons": 0,
            "total_lessons": 0,
            "percent": 0,
        }

    current_level = available_levels[-1]

    for level in available_levels:
        level_total = totals[level]

        level_completed = completed.get(
            level,
            0,
        )

        if level_completed < level_total:
            current_level = level
            break

    current_index = (
        available_levels.index(
            current_level
        )
    )

    if (
        current_index + 1
        < len(available_levels)
    ):
        next_level = available_levels[
            current_index + 1
        ]
    else:
        next_level = None

    total_lessons = totals.get(
        current_level,
        0,
    )

    completed_lessons = min(
        completed.get(
            current_level,
            0,
        ),
        total_lessons,
    )

    if total_lessons:
        percent = round(
            completed_lessons
            / total_lessons
            * 100
        )
    else:
        percent = 0

    return {
        "current_level": current_level,
        "next_level": next_level,
        "completed_lessons": (
            completed_lessons
        ),
        "total_lessons": total_lessons,
        "percent": percent,
    }


def build_week_activity(
    completed_attempts,
):
    """
    Возвращает активность с понедельника
    по воскресенье.
    """

    today = timezone.localdate()

    week_start = (
        today
        - timedelta(
            days=today.weekday()
        )
    )

    week_end = (
        week_start
        + timedelta(days=6)
    )

    rows = (
        completed_attempts
        .filter(
            completed_at__date__range=(
                week_start,
                week_end,
            )
        )
        .annotate(
            day=TruncDate(
                "completed_at"
            )
        )
        .values("day")
        .annotate(
            completed_attempts_count=(
                Count("id")
            ),
            total_seconds=Sum(
                "duration_seconds"
            ),
        )
        .order_by("day")
    )

    rows_by_day = {
        row["day"]: row
        for row in rows
    }

    result = []

    for offset in range(7):
        day = (
            week_start
            + timedelta(days=offset)
        )

        row = rows_by_day.get(day)

        if row is None:
            attempts_count = 0
            minutes = 0
        else:
            attempts_count = row[
                "completed_attempts_count"
            ]

            minutes = round(
                (
                    row["total_seconds"]
                    or 0
                )
                / 60
            )

        result.append(
            {
                "date": day,
                "completed_attempts": (
                    attempts_count
                ),
                "minutes": minutes,
            }
        )

    return result


def build_speaking_stats(
    user,
):
    completed_attempts = (
        SpeakingAttempt.objects
        .filter(
            user=user,
            status=(
                SpeakingAttempt
                .Status.COMPLETED
            ),
            completed_at__isnull=False,
        )
    )

    aggregate = (
        completed_attempts.aggregate(
            completed_attempts_count=(
                Count("id")
            ),
            completed_lessons_count=(
                Count(
                    "lesson_id",
                    distinct=True,
                )
            ),
            total_seconds=Sum(
                "duration_seconds"
            ),
            average_score=Avg(
                "feedback__overall_score"
            ),
        )
    )

    active_days = set(
        completed_attempts
        .annotate(
            day=TruncDate(
                "completed_at"
            )
        )
        .values_list(
            "day",
            flat=True,
        )
    )

    total_minutes = round(
        (
            aggregate["total_seconds"]
            or 0
        )
        / 60
    )

    average_score = round(
        aggregate["average_score"]
        or 0
    )

    return {
        "summary": {
            "day_streak": (
                calculate_streak(
                    active_days
                )
            ),
            "total_minutes": (
                total_minutes
            ),
            "average_score": (
                average_score
            ),
            "completed_attempts": (
                aggregate[
                    "completed_attempts_count"
                ]
            ),
            "completed_lessons": (
                aggregate[
                    "completed_lessons_count"
                ]
            ),
        },
        "level_progress": (
            build_level_progress(user)
        ),
        "week": (
            build_week_activity(
                completed_attempts
            )
        ),
    }