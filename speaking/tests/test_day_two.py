from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course, Lesson
from speaking.models import (
    LessonSpeakingConfig,
    SpeakingAttempt,
)
from speaking.services.storage import (
    AudioObjectNotFound,
)


User = get_user_model()


@override_settings(
    AWS_S3_SPEAKING_BUCKET=(
        "test-speaking-bucket"
    ),
    AWS_S3_PRESIGNED_EXPIRES=900,
    SPEAKING_MAX_AUDIO_SIZE_BYTES=1024,
)
class SpeakingDayTwoTests(
    APITestCase
):
    def setUp(self):
        self.owner = (
            User.objects.create_user(
                email=(
                    "owner-day-two@test.com"
                ),
                password="password123",
            )
        )

        self.student = (
            User.objects.create_user(
                email=(
                    "student-day-two@test.com"
                ),
                password="password123",
            )
        )

        self.other_user = (
            User.objects.create_user(
                email=(
                    "other-day-two@test.com"
                ),
                password="password123",
            )
        )

        self.course = (
            Course.objects.create(
                name=(
                    "Speaking Upload Course"
                ),
                owner=self.owner,
            )
        )

        self.lesson = (
            Lesson.objects.create(
                name=(
                    "Speaking Upload Lesson"
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
                    "Source transcript."
                ),
                reference_summary=(
                    "Reference summary."
                ),
                key_points=[
                    "Main point",
                ],
                target_duration_seconds=60,
            )
        )

        self.client.force_authenticate(
            self.student
        )

    @patch(
        (
            "speaking.services.uploads."
            "generate_presigned_upload"
        )
    )
    def test_create_attempt_returns_presigned_upload(
        self,
        mock_generate_upload,
    ):
        mock_generate_upload.return_value = {
            "url": (
                "https://example.com/upload"
            ),
            "method": "PUT",
            "headers": {
                "Content-Type": "audio/mp4",
            },
            "expires_in": 900,
        }

        response = self.client.post(
            (
                f"/api/lessons/"
                f"{self.lesson.public_id}/"
                "speaking-attempts/"
            ),
            data={
                "content_type": "audio/mp4",
                "file_extension": "m4a",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["status"],
            "created",
        )

        self.assertEqual(
            response.data["upload"][
                "method"
            ],
            "PUT",
        )

        attempt = (
            SpeakingAttempt.objects.get(
                user=self.student,
                lesson=self.lesson,
            )
        )

        self.assertEqual(
            attempt.audio_content_type,
            "audio/mp4",
        )

        self.assertTrue(
            attempt.audio_key.endswith(
                ".m4a"
            )
        )

        self.assertIn(
            str(self.lesson.public_id),
            attempt.audio_key,
        )

        self.assertIn(
            str(attempt.public_id),
            attempt.audio_key,
        )

        (
            mock_generate_upload
            .assert_called_once_with(
                key=attempt.audio_key,
                content_type="audio/mp4",
            )
        )

    def test_create_attempt_rejects_invalid_content_type(
        self,
    ):
        response = self.client.post(
            (
                f"/api/lessons/"
                f"{self.lesson.public_id}/"
                "speaking-attempts/"
            ),
            data={
                "content_type": "audio/wav",
                "file_extension": "m4a",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            SpeakingAttempt.objects.count(),
            0,
        )

    def test_create_attempt_requires_speaking_config(
        self,
    ):
        lesson_without_config = (
            Lesson.objects.create(
                name=(
                    "Lesson without speaking"
                ),
                course=self.course,
                owner=self.owner,
            )
        )

        response = self.client.post(
            (
                f"/api/lessons/"
                f"{lesson_without_config.public_id}/"
                "speaking-attempts/"
            ),
            data={
                "content_type": "audio/mp4",
                "file_extension": "m4a",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    @patch(
        (
            "speaking.services.uploads."
            "head_audio_object"
        )
    )
    def test_complete_upload_saves_metadata(
        self,
        mock_head_audio,
    ):
        attempt = self.create_attempt()

        mock_head_audio.return_value = {
            "size_bytes": 512,
            "content_type": "audio/mp4",
        }

        response = self.client.post(
            (
                f"/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "uploaded",
        )

        self.assertEqual(
            response.data["audio"][
                "size_bytes"
            ],
            512,
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            (
                SpeakingAttempt
                .Status.UPLOADED
            ),
        )

        self.assertEqual(
            attempt.audio_size_bytes,
            512,
        )

        self.assertIsNotNone(
            attempt.uploaded_at
        )

    @patch(
        (
            "speaking.services.uploads."
            "head_audio_object"
        )
    )
    def test_complete_upload_is_idempotent(
        self,
        mock_head_audio,
    ):
        attempt = self.create_attempt(
            status=(
                SpeakingAttempt
                .Status.UPLOADED
            ),
            audio_size_bytes=512,
        )

        response = self.client.post(
            (
                f"/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "uploaded",
        )

        mock_head_audio.assert_not_called()

    @patch(
        (
            "speaking.services.uploads."
            "head_audio_object"
        )
    )
    def test_complete_upload_rejects_missing_object(
        self,
        mock_head_audio,
    ):
        attempt = self.create_attempt()

        mock_head_audio.side_effect = (
            AudioObjectNotFound()
        )

        response = self.client.post(
            (
                f"/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            (
                SpeakingAttempt
                .Status.CREATED
            ),
        )

    @patch(
        (
            "speaking.services.uploads."
            "delete_audio_object"
        )
    )
    @patch(
        (
            "speaking.services.uploads."
            "head_audio_object"
        )
    )
    def test_complete_upload_rejects_large_file(
        self,
        mock_head_audio,
        mock_delete_audio,
    ):
        attempt = self.create_attempt()

        mock_head_audio.return_value = {
            "size_bytes": 2048,
            "content_type": "audio/mp4",
        }

        response = self.client.post(
            (
                f"/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        (
            mock_delete_audio
            .assert_called_once_with(
                key=attempt.audio_key,
            )
        )

    @patch(
        (
            "speaking.services.uploads."
            "delete_audio_object"
        )
    )
    @patch(
        (
            "speaking.services.uploads."
            "head_audio_object"
        )
    )
    def test_complete_upload_rejects_wrong_content_type(
        self,
        mock_head_audio,
        mock_delete_audio,
    ):
        attempt = self.create_attempt()

        mock_head_audio.return_value = {
            "size_bytes": 512,
            "content_type": "audio/wav",
        }

        response = self.client.post(
            (
                f"/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        (
            mock_delete_audio
            .assert_called_once_with(
                key=attempt.audio_key,
            )
        )

    def test_user_cannot_complete_another_users_attempt(
        self,
    ):
        attempt = self.create_attempt(
            user=self.other_user,
        )

        response = self.client.post(
            (
                f"/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            data={},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def create_attempt(
        self,
        *,
        user=None,
        status=(
            SpeakingAttempt.Status.CREATED
        ),
        audio_size_bytes=None,
    ):
        return (
            SpeakingAttempt.objects.create(
                user=(
                    user
                    or self.student
                ),
                lesson=self.lesson,
                attempt_number=1,
                status=status,
                audio_key=(
                    f"speaking/"
                    f"{self.lesson.public_id}/"
                    "test-attempt.m4a"
                ),
                audio_content_type=(
                    "audio/mp4"
                ),
                audio_size_bytes=(
                    audio_size_bytes
                ),
            )
        )