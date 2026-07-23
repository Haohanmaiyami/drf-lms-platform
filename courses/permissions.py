from rest_framework.permissions import BasePermission

MODERATORS = "moderators"


class IsModer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.groups.filter(name=MODERATORS).exists()
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class NotModer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and not user.groups.filter(name=MODERATORS).exists()
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "owner", None)
        if owner is None and hasattr(obj, "course"):
            owner = getattr(obj.course, "owner", None)
        return owner == request.user


def has_course_access(user, course):
    """
    В LingLoop MVP все учебные материалы доступны
    любому авторизованному пользователю.

    Параметр course сохраняется в сигнатуре,
    чтобы не ломать существующие вызовы.
    """

    return bool(
        user
        and user.is_authenticated
        and course is not None
    )