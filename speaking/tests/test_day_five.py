import json
from uuid import uuid4

from django.urls import reverse
from django.contrib.auth import (
    get_user_model,
)
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import (
    Course,
    Lesson,
)
from speaking.models import (
    LessonSpeakingConfig,
    SpeakingAttempt,
    SpeakingFeedback,
)
from speaking.serializers import (
    SpeakingAttemptCreateResponseSerializer,
)


User = get_user_model()


class SpeakingDayFiveContractTests(
    APITestCase
):
    def setUp(self):
        self.owner = (
            User.objects.create_user(
                email=(
                    "owner-day-five@test.com"
                ),
                password="password123",
            )
        )

        self.student = (
            User.objects.create_user(
                email=(
                    "student-day-five@test.com"
                ),
                password="password123",
            )
        )

        self.other_user = (
            User.objects.create_user(
                email=(
                    "other-day-five@test.com"
                ),
                password="password123",
            )
        )

        self.course = (
            Course.objects.create(
                name=(
                    "Day Five Course"
                ),
                owner=self.owner,
            )
        )

        self.lesson = (
            Lesson.objects.create(
                name=(
                    "Day Five Lesson"
                ),
                course=self.course,
                owner=self.owner,
            )
        )

        (
            LessonSpeakingConfig
            .objects.create(
                lesson=self.lesson,
                source_transcript=(
                    "A customer enters a cafe "
                    "and orders coffee."
                ),
                reference_summary=(
                    "A customer orders coffee."
                ),
                key_points=[
                    "The customer enters a cafe",
                    "The customer orders coffee",
                ],
                target_duration_seconds=45,
            )
        )

    def create_attempt(
        self,
        *,
        user=None,
        attempt_number=1,
        attempt_status=(
            SpeakingAttempt.Status.ANALYZING
        ),
        with_metrics=False,
    ):
        values = {
            "user": user or self.student,
            "lesson": self.lesson,
            "attempt_number": attempt_number,
            "status": attempt_status,
            "audio_key": (
                "speaking/internal/"
                "private-audio-key.m4a"
            ),
            "audio_content_type": (
                "audio/mp4"
            ),
            "audio_size_bytes": 1024,
            "uploaded_at": timezone.now(),
        }

        if with_metrics:
            values.update(
                {
                    "transcript": (
                        "The customer entered "
                        "the cafe and ordered "
                        "a coffee."
                    ),
                    "duration_seconds": 40.0,
                    "word_count": 10,
                    "words_per_minute": 15.0,
                    "filler_word_count": 1,
                }
            )

        if (
            attempt_status
            == SpeakingAttempt.Status.COMPLETED
        ):
            values["completed_at"] = (
                timezone.now()
            )

        return (
            SpeakingAttempt.objects.create(
                **values
            )
        )

    def create_feedback(
        self,
        *,
        attempt,
    ):
        return (
            SpeakingFeedback.objects.create(
                attempt=attempt,
                overall_score=84,
                meaning_score=90,
                compression_score=80,
                clarity_score=85,
                grammar_score=88,
                vocabulary_score=82,
                fluency_score=78,
                covered_key_points=[
                    (
                        "The customer "
                        "orders coffee"
                    )
                ],
                missed_key_points=[
                    (
                        "The customer "
                        "enters a cafe"
                    )
                ],
                unnecessary_details=[],
                corrections=[
                    {
                        "original": (
                            "He order coffee"
                        ),
                        "corrected": (
                            "He orders coffee"
                        ),
                        "explanation": (
                            "Use -s with "
                            "third-person singular."
                        ),
                    }
                ],
                short_feedback=(
                    "The main idea was clear."
                ),
                concise_version=(
                    "The customer orders coffee."
                ),
                next_goal=(
                    "Finish in 45 seconds."
                ),
            )
        )

    def test_all_speaking_endpoints_require_authentication(
        self,
    ):
        attempt_id = uuid4()

        requests = [
            (
                "get",
                (
                    "/api/lessons/"
                    f"{self.lesson.public_id}/"
                    "speaking-attempts/"
                ),
                None,
            ),
            (
                "post",
                (
                    "/api/lessons/"
                    f"{self.lesson.public_id}/"
                    "speaking-attempts/"
                ),
                {
                    "content_type": (
                        "audio/mp4"
                    ),
                    "file_extension": "m4a",
                },
            ),
            (
                "get",
                (
                    "/api/speaking-attempts/"
                    f"{attempt_id}/"
                ),
                None,
            ),
            (
                "post",
                (
                    "/api/speaking-attempts/"
                    f"{attempt_id}/"
                    "complete-upload/"
                ),
                {},
            ),
        ]

        for method, url, data in requests:
            with self.subTest(
                method=method,
                url=url,
            ):
                request_method = getattr(
                    self.client,
                    method,
                )

                if data is None:
                    response = request_method(
                        url
                    )
                else:
                    response = request_method(
                        url,
                        data=data,
                        format="json",
                    )

                self.assertEqual(
                    response.status_code,
                    status
                    .HTTP_401_UNAUTHORIZED,
                )

    def test_history_contract_is_paginated_and_private(
        self,
    ):
        first_attempt = self.create_attempt(
            attempt_number=1,
            attempt_status=(
                SpeakingAttempt
                .Status.COMPLETED
            ),
            with_metrics=True,
        )

        self.create_feedback(
            attempt=first_attempt,
        )

        second_attempt = self.create_attempt(
            attempt_number=2,
            attempt_status=(
                SpeakingAttempt
                .Status.ANALYZING
            ),
            with_metrics=True,
        )

        self.create_attempt(
            user=self.other_user,
            attempt_number=1,
            attempt_status=(
                SpeakingAttempt
                .Status.COMPLETED
            ),
            with_metrics=True,
        )

        self.client.force_authenticate(
            self.student
        )

        response = self.client.get(
            (
                "/api/lessons/"
                f"{self.lesson.public_id}/"
                "speaking-attempts/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            set(response.data.keys()),
            {
                "count",
                "next",
                "previous",
                "results",
            },
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

        self.assertEqual(
            len(response.data["results"]),
            2,
        )

        self.assertEqual(
            response.data["results"][0][
                "id"
            ],
            str(second_attempt.public_id),
        )

        result_keys = {
            "id",
            "lesson_id",
            "attempt_number",
            "status",
            "duration_seconds",
            "words_per_minute",
            "overall_score",
            "created_at",
            "completed_at",
        }

        self.assertEqual(
            set(
                response.data[
                    "results"
                ][0].keys()
            ),
            result_keys,
        )

        returned_ids = {
            item["id"]
            for item
            in response.data["results"]
        }

        other_attempt_ids = {
            str(public_id)
            for public_id
            in SpeakingAttempt.objects
            .filter(user=self.other_user)
            .values_list(
                "public_id",
                flat=True,
            )
        }

        self.assertTrue(
            returned_ids.isdisjoint(
                other_attempt_ids
            )
        )

    def test_processing_detail_contract(
        self,
    ):
        attempt = self.create_attempt(
            attempt_number=1,
            attempt_status=(
                SpeakingAttempt
                .Status.ANALYZING
            ),
            with_metrics=True,
        )

        self.client.force_authenticate(
            self.student
        )

        response = self.client.get(
            (
                "/api/speaking-attempts/"
                f"{attempt.public_id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            set(response.data.keys()),
            {
                "id",
                "lesson_id",
                "attempt_number",
                "status",
                "transcript",
                "metrics",
                "comparison",
                "feedback",
                "error",
                "created_at",
                "uploaded_at",
                "completed_at",
            },
        )

        self.assertEqual(
            response.data["status"],
            "analyzing",
        )

        self.assertIsNotNone(
            response.data["metrics"]
        )

        self.assertIsNone(
            response.data["feedback"]
        )

        self.assertIsNone(
            response.data["error"]
        )

        self.assertNotIn(
            "audio_key",
            response.data,
        )

        self.assertNotIn(
            "user",
            response.data,
        )

    def test_failed_detail_returns_safe_error(
        self,
    ):
        attempt = self.create_attempt(
            attempt_number=1,
            attempt_status=(
                SpeakingAttempt.Status.FAILED
            ),
        )

        attempt.error_code = (
            "empty_transcript"
        )
        attempt.error_message = (
            "The recording did not contain "
            "recognizable speech."
        )
        attempt.save(
            update_fields=[
                "error_code",
                "error_message",
            ]
        )

        self.client.force_authenticate(
            self.student
        )

        response = self.client.get(
            (
                "/api/speaking-attempts/"
                f"{attempt.public_id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "failed",
        )

        self.assertEqual(
            response.data["error"],
            {
                "code": (
                    "empty_transcript"
                ),
                "message": (
                    "The recording did not "
                    "contain recognizable speech."
                ),
            },
        )

        serialized_text = json.dumps(
            response.data
        )

        self.assertNotIn(
            attempt.audio_key,
            serialized_text,
        )

        self.assertNotIn(
            "AWS_SECRET_ACCESS_KEY",
            serialized_text,
        )

    def test_completed_detail_returns_feedback(
        self,
    ):
        attempt = self.create_attempt(
            attempt_number=1,
            attempt_status=(
                SpeakingAttempt
                .Status.COMPLETED
            ),
            with_metrics=True,
        )

        self.create_feedback(
            attempt=attempt,
        )

        self.client.force_authenticate(
            self.student
        )

        response = self.client.get(
            (
                "/api/speaking-attempts/"
                f"{attempt.public_id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "completed",
        )

        self.assertIsNone(
            response.data["error"]
        )

        self.assertEqual(
            set(
                response.data[
                    "feedback"
                ].keys()
            ),
            {
                "overall_score",
                "meaning_score",
                "compression_score",
                "clarity_score",
                "grammar_score",
                "vocabulary_score",
                "fluency_score",
                "covered_key_points",
                "missed_key_points",
                "unnecessary_details",
                "corrections",
                "short_feedback",
                "concise_version",
                "next_goal",
            },
        )

        self.assertEqual(
            response.data["feedback"][
                "overall_score"
            ],
            84,
        )

        self.assertEqual(
            response.data["feedback"][
                "next_goal"
            ],
            "Finish in 45 seconds.",
        )

    def test_swagger_contains_lingloop_speaking_contract(
        self,
    ):
        swagger_url = reverse(
            "schema-json",
            kwargs={
                "format": "json",
            },
        )

        response = self.client.get(
            swagger_url,
            secure=True,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        schema = json.loads(
            response.content.decode(
                "utf-8"
            )
        )

        self.assertEqual(
            schema["info"]["title"],
            "LingLoop API",
        )

        paths = list(
            schema["paths"].keys()
        )

        self.assertTrue(
            any(
                path.endswith(
                    (
                        "/lessons/"
                        "{lesson_id}/"
                        "speaking-attempts/"
                    )
                )
                for path in paths
            )
        )

        self.assertTrue(
            any(
                path.endswith(
                    (
                        "/speaking-attempts/"
                        "{attempt_id}/"
                    )
                )
                for path in paths
            )
        )

        self.assertTrue(
            any(
                path.endswith(
                    (
                        "/speaking-attempts/"
                        "{attempt_id}/"
                        "complete-upload/"
                    )
                )
                for path in paths
            )
        )

    def test_response_serializer_rejects_unknown_status(
        self,
    ):
        serializer = (
            SpeakingAttemptCreateResponseSerializer(
                data={
                    "id": uuid4(),
                    "lesson_id": (
                        self.lesson.public_id
                    ),
                    "attempt_number": 1,
                    "status": (
                        "unknown-status"
                    ),
                    "upload": {
                        "url": (
                            "https://example.com/"
                            "upload"
                        ),
                        "method": "PUT",
                        "headers": {
                            "Content-Type": (
                                "audio/mp4"
                            ),
                        },
                        "expires_in": 900,
                    },
                }
            )
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "status",
            serializer.errors,
        )