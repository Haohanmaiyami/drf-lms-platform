from courses.permissions import has_course_access


def has_lesson_access(user, lesson) -> bool:
    """Проверяет доступ к уроку по правилам LingLoop MVP."""

    if lesson is None:
        return False

    return has_course_access(
        user,
        lesson.course,
    )