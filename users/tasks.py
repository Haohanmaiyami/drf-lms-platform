import os
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone


@shared_task
def deactivate_inactive_users():
    """
    Деактивирует пользователей, которые не логинились более X дней.
    X берём из USER_INACTIVE_DAYS (по умолчанию 30).
    """
    User = get_user_model()
    days = int(os.getenv("USER_INACTIVE_DAYS", "30"))

    now = timezone.now()
    cutoff = now - timedelta(days=days)

    # last_login < cutoff  ИЛИ  (last_login IS NULL и date_joined < cutoff)
    stale = Q(last_login__lt=cutoff) | (Q(last_login__isnull=True) & Q(date_joined__lt=cutoff))

    qs = (
        User.objects
        .filter(is_active=True, is_staff=False, is_superuser=False)
        .filter(stale)
    )

    updated = qs.update(is_active=False)

    return f"Deactivated {updated} users older than {days} days"