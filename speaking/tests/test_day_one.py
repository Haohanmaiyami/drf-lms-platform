from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import (
    Course,
    Lesson,
    Subscription,
)
from speaking.models import (
    LessonSpeakingConfig,
    SpeakingAttempt,
)
from speaking.services.attempts import (
    create_speaking_attempt,
)


User = get_user_model()


class SpeakingDayOneTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@test.com",
            password="password123",
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            email="other@test.com",
            password="password123",
        )

        self.course = Course.objects.create(
            name="English Retelling",
            owner=self.owner,
        )

        self.lesson = Lesson.objects.create(
            name="Ordering Coffee",
            course=self.course,
            owner=self.owner,
            video=(
                "https://youtu.be/"
                "dQw4w9WgXcQ"
            ),
        )

        Subscription.objects.create(
            user=self.student,
            course=self.course,
        )

        self.config = (
            LessonSpeakingConfig.objects.create(
                lesson=self.lesson,
                source_transcript=(
                    "The customer orders a coffee..."
                ),
                reference_summary=(
                    "A customer orders coffee "
                    "and chooses the size."
                ),
                key_points=[
                    "The customer orders coffee",
                    "The barista asks about size",
                ],
                target_duration_seconds=45,
            )
        )

    def test_lesson_contains_speaking_configuration(self):
        self.client.force_authenticate(
            self.student
        )

        response = self.client.get(
            f"/api/lessons/"
            f"{self.lesson.public_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["speaking_enabled"]
        )

        self.assertEqual(
            response.data[
                "target_duration_seconds"
            ],
            45,
        )

    def test_attempt_numbers_increment(self):
        first_attempt = create_speaking_attempt(
            user=self.student,
            lesson=self.lesson,
        )

        second_attempt = create_speaking_attempt(
            user=self.student,
            lesson=self.lesson,
        )

        self.assertEqual(
            first_attempt.attempt_number,
            1,
        )

        self.assertEqual(
            second_attempt.attempt_number,
            2,
        )

    def test_user_sees_only_own_attempts(self):
        SpeakingAttempt.objects.create(
            user=self.student,
            lesson=self.lesson,
            attempt_number=1,
        )

        SpeakingAttempt.objects.create(
            user=self.owner,
            lesson=self.lesson,
            attempt_number=1,
        )

        self.client.force_authenticate(
            self.student
        )

        response = self.client.get(
            f"/api/lessons/"
            f"{self.lesson.public_id}/"
            f"speaking-attempts/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

    def test_user_cannot_open_another_users_attempt(self):
        attempt = SpeakingAttempt.objects.create(
            user=self.student,
            lesson=self.lesson,
            attempt_number=1,
        )

        self.client.force_authenticate(
            self.other_user
        )

        response = self.client.get(
            f"/api/speaking-attempts/"
            f"{attempt.public_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )