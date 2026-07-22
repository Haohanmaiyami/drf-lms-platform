from courses.permissions import (
    MODERATORS,
    has_course_access,
)


def has_lesson_access(user, lesson) -> bool:
    if not user or not user.is_authenticated:
        return False

    if lesson.owner_id == user.id:
        return True

    if user.groups.filter(name=MODERATORS).exists():
        return True

    return has_course_access(
        user,
        lesson.course,
    )