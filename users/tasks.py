from urllib.parse import urlencode

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_encode


User = get_user_model()


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    ignore_result=True,
)
def send_password_reset_email(email):
    user = (
        User.objects
        .filter(
            email__iexact=email,
            is_active=True,
        )
        .first()
    )

    if user is None or not user.has_usable_password():
        return

    uid = urlsafe_base64_encode(
        force_bytes(user.pk)
    )
    token = default_token_generator.make_token(user)

    query = urlencode({
        "uid": uid,
        "token": token,
    })

    reset_link = (
        f"{settings.PASSWORD_RESET_URL}?{query}"
    )

    text_body = (
        "We received a request to reset your password.\n\n"
        f"{reset_link}\n\n"
        "If you did not request this, "
        "you can ignore this email."
    )

    html_body = format_html(
        "<p>We received a request to reset your password.</p>"
        '<p><a href="{}">Reset password</a></p>'
        "<p>If you did not request this, "
        "you can ignore this email.</p>",
        reset_link,
    )

    message = EmailMultiAlternatives(
        subject="Reset your password",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    message.attach_alternative(
        html_body,
        "text/html",
    )

    message.send(fail_silently=False)


@shared_task
def deactivate_inactive_users():
    """
    Auto-deactivation disabled.

    We no longer deactivate users automatically because it
    prevents legitimate users from logging in.
    """
    return "Auto-deactivation is disabled."