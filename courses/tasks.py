from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

from .models import Course, Subscription


@shared_task
def send_course_update_email(course_id: int):
    """
    Асинхронная рассылка писем подписчикам курса при обновлении.
    Отправляем всего одно письмо с BCC как в письмах скрытым вместе всего цикла
    """
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return "Course not found"

    # Собираем всех подписчиков (их email)
    emails = list({
        s.user.email
        for s in (
            Subscription.objects
            .select_related("user")
            .filter(course_id=course_id, user__is_active=True)
            .exclude(user__email__isnull=True)
            .exclude(user__email="")
        )
        if s.user.email
    })

    if not emails:
        return "No recipients"

    subject = f"Обновление курса: {course.name}"
    body = (
        "Здравствуйте!\n\n"
        f"В курсе «{course.name}» появились новые материалы.\n"
        "Зайдите в личный кабинет и посмотрите обновления."
    )

    # Один вызов отправки; реальные получатели в BCC (приватность)
    msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.DEFAULT_FROM_EMAIL],
        bcc=emails,
    )
    msg.send(fail_silently=False)

    return f"Sent to {len(emails)} recipients"


@shared_task
def heartbeat():
    print("test")

