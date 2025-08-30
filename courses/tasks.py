
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Course, Subscription

@shared_task
def send_course_update_email(course_id: int):
    """
    Асинхронная рассылка писем подписчикам курса при обновлении.
    """
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return "Course not found"

    subs = (
        Subscription.objects
        .filter(course_id=course_id, user__is_active=True)
        .exclude(user__email__isnull=True)
        .exclude(user__email="")
        .select_related("user")
    )

    subject = f"Обновление курса: {course.name}"
    message = (
        f"Здравствуйте!\n\n"
        f"В курсе «{course.name}» появились новые материалы.\n"
        f"Зайдите в личный кабинет и посмотрите обновления."
    )
    from_email = settings.DEFAULT_FROM_EMAIL

    sent = 0
    for sub in subs:
        send_mail(subject, message, from_email, [sub.user.email], fail_silently=False)
        sent += 1

    return f"Sent {sent} emails"



@shared_task
def heartbeat():
    print("test")

