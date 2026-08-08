from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import (
    default_token_generator,
)
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from users.tasks import send_password_reset_email


User = get_user_model()

GENERIC_RESPONSE = {
    "detail": (
        "If this email exists, "
        "a reset link has been sent."
    )
}


class PasswordResetRequestTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            email="user@example.com",
            password="Old-password-2026!",
        )

        self.url = reverse(
            "users:password-reset"
        )

    @patch(
        "users.views."
        "send_password_reset_email.delay"
    )
    def test_response_never_contains_token(
        self,
        delay,
    ):
        response = self.client.post(
            self.url,
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            GENERIC_RESPONSE,
        )
        self.assertNotIn(
            "uid",
            response.data,
        )
        self.assertNotIn(
            "token",
            response.data,
        )

        delay.assert_called_once_with(
            self.user.email
        )

    @patch(
        "users.views."
        "send_password_reset_email.delay"
    )
    def test_unknown_email_has_same_response(
        self,
        delay,
    ):
        response = self.client.post(
            self.url,
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            GENERIC_RESPONSE,
        )

        delay.assert_called_once_with(
            "unknown@example.com"
        )

    @patch(
        "users.views."
        "send_password_reset_email.delay"
    )
    def test_email_rate_limit(
        self,
        delay,
    ):
        for _ in range(3):
            response = self.client.post(
                self.url,
                {"email": self.user.email},
                format="json",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
            )

        response = self.client.post(
            self.url,
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


class PasswordResetConfirmTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.user = User.objects.create_user(
            email="user@example.com",
            password="Old-password-2026!",
        )

        self.url = reverse(
            "users:password-reset-confirm"
        )

    def make_payload(self):
        return {
            "uid": urlsafe_base64_encode(
                force_bytes(self.user.pk)
            ),
            "token": (
                default_token_generator
                .make_token(self.user)
            ),
            "new_password": (
                "New-password-2026!"
            ),
        }

    def test_valid_token_changes_password(self):
        payload = self.make_payload()

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "New-password-2026!"
            )
        )
        self.assertIsNone(
            self.user.last_login
        )

    def test_token_cannot_be_reused(self):
        payload = self.make_payload()

        first_response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        second_response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_reset_does_not_reactivate_user(
        self
    ):
        self.user.is_active = False
        self.user.save(
            update_fields=["is_active"]
        )

        payload = self.make_payload()

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_active
        )


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends."
        "locmem.EmailBackend"
    ),
    PASSWORD_RESET_URL=(
        "https://example.com/api/reset-password/"
    ),
)
class PasswordResetEmailTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="Old-password-2026!",
        )

    def test_email_is_sent_for_existing_user(
        self
    ):
        send_password_reset_email.run(
            self.user.email
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )
        self.assertIn(
            "https://example.com/"
            "api/reset-password/?uid=",
            mail.outbox[0].body,
        )
        self.assertIn(
            "&token=",
            mail.outbox[0].body,
        )

    def test_email_is_not_sent_for_unknown_user(
        self
    ):
        send_password_reset_email.run(
            "unknown@example.com"
        )

        self.assertEqual(
            len(mail.outbox),
            0,
        )