from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)
from django.test import override_settings
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
from speaking.services.metrics import (
    calculate_speech_metrics,
)
from speaking.tasks import (
    poll_speaking_transcription,
    process_speaking_attempt,
)


User = get_user_model()


@override_settings(
    AWS_S3_SPEAKING_BUCKET=(
        "test-speaking-bucket"
    ),
    AWS_TRANSCRIBE_OUTPUT_PREFIX=(
        "transcriptions"
    ),
    AWS_TRANSCRIBE_POLL_SECONDS=1,
    AWS_TRANSCRIBE_MAX_POLLS=10,
)
class SpeakingDayThreeTests(
    APITestCase
):
    def setUp(self):
        self.owner = (
            User.objects.create_user(
                email=(
                    "owner-day-three@test.com"
                ),
                password="password123",
            )
        )

        self.student = (
            User.objects.create_user(
                email=(
                    "student-day-three@test.com"
                ),
                password="password123",
            )
        )

        self.course = (
            Course.objects.create(
                name=(
                    "Speaking Day Three Course"
                ),
                owner=self.owner,
            )
        )

        self.lesson = (
            Lesson.objects.create(
                name=(
                    "Speaking Day Three Lesson"
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
                    "The speaker explains "
                    "the main idea."
                ),
                reference_summary=(
                    "A short explanation "
                    "of the main idea."
                ),
                key_points=[
                    "The main idea",
                ],
                target_duration_seconds=60,
            )
        )

        (
            Subscription.objects.create(
                user=self.student,
                course=self.course,
            )
        )

        self.client.force_authenticate(
            self.student
        )

    def create_attempt(
        self,
        *,
        attempt_number=1,
        attempt_status=None,
    ):
        if attempt_status is None:
            attempt_status = (
                SpeakingAttempt.Status.CREATED
            )

        return (
            SpeakingAttempt.objects.create(
                user=self.student,
                lesson=self.lesson,
                attempt_number=(
                    attempt_number
                ),
                status=attempt_status,
                audio_key=(
                    "speaking/test/audio.m4a"
                ),
                audio_content_type=(
                    "audio/mp4"
                ),
                audio_size_bytes=1024,
            )
        )

    # 1. complete-upload запускает Celery

    @patch(
        "speaking.views."
        "process_speaking_attempt."
        "delay_on_commit"
    )
    @patch(
        "speaking.views."
        "complete_attempt_upload"
    )
    def test_complete_upload_starts_celery(
        self,
        mocked_complete_upload,
        mocked_delay_on_commit,
    ):
        attempt = self.create_attempt()

        attempt.status = (
            SpeakingAttempt.Status.UPLOADED
        )

        mocked_complete_upload.return_value = (
            attempt,
            True,
        )

        response = self.client.post(
            (
                "/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mocked_delay_on_commit.assert_called_once_with(
            attempt.pk
        )

    # 2. Повторный complete-upload
    # не запускает Celery снова

    @patch(
        "speaking.views."
        "process_speaking_attempt."
        "delay_on_commit"
    )
    @patch(
        "speaking.views."
        "complete_attempt_upload"
    )
    def test_repeated_complete_upload_does_not_start_celery(
        self,
        mocked_complete_upload,
        mocked_delay_on_commit,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt.Status.UPLOADED
            )
        )

        mocked_complete_upload.return_value = (
            attempt,
            False,
        )

        response = self.client.post(
            (
                "/api/speaking-attempts/"
                f"{attempt.public_id}/"
                "complete-upload/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mocked_delay_on_commit.assert_not_called()

    # 3. uploaded меняется
    # на transcribing

    @patch(
        "speaking.tasks."
        "poll_speaking_transcription."
        "apply_async"
    )
    @patch(
        "speaking.tasks."
        "start_transcription_job"
    )
    def test_uploaded_changes_to_transcribing(
        self,
        mocked_start_job,
        mocked_poll_apply_async,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt.Status.UPLOADED
            )
        )

        mocked_start_job.return_value = {
            "job_name": (
                f"lingloop-{attempt.public_id}"
            ),
            "output_key": (
                "transcriptions/result.json"
            ),
        }

        process_speaking_attempt.run(
            attempt.pk
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            SpeakingAttempt
            .Status
            .TRANSCRIBING,
        )

    # 4. Amazon Transcribe job
    # действительно запускается

    @patch(
        "speaking.tasks."
        "poll_speaking_transcription."
        "apply_async"
    )
    @patch(
        "speaking.tasks."
        "start_transcription_job"
    )
    def test_transcribe_job_is_started(
        self,
        mocked_start_job,
        mocked_poll_apply_async,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt.Status.UPLOADED
            )
        )

        mocked_start_job.return_value = {
            "job_name": (
                f"lingloop-{attempt.public_id}"
            ),
            "output_key": (
                "transcriptions/result.json"
            ),
        }

        process_speaking_attempt.run(
            attempt.pk
        )

        mocked_start_job.assert_called_once()

        started_attempt = (
            mocked_start_job
            .call_args
            .kwargs["attempt"]
        )

        self.assertEqual(
            started_attempt.pk,
            attempt.pk,
        )

    # 5. analyzing-попытка
    # повторно не обрабатывается

    @patch(
        "speaking.tasks."
        "start_transcription_job"
    )
    def test_analyzing_attempt_is_not_processed_again(
        self,
        mocked_start_job,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt.Status.ANALYZING
            )
        )

        result = (
            process_speaking_attempt.run(
                attempt.pk
            )
        )

        mocked_start_job.assert_not_called()

        self.assertEqual(
            result,
            "Attempt skipped.",
        )

    # 6. IN_PROGRESS планирует
    # следующую проверку

    @patch(
        "speaking.tasks."
        "schedule_next_poll"
    )
    @patch(
        "speaking.tasks."
        "get_transcription_job"
    )
    def test_in_progress_schedules_next_poll(
        self,
        mocked_get_job,
        mocked_schedule_next_poll,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt
                .Status
                .TRANSCRIBING
            )
        )

        mocked_get_job.return_value = {
            "status": "IN_PROGRESS",
            "failure_reason": "",
        }

        result = (
            poll_speaking_transcription.run(
                attempt.pk,
                2,
            )
        )

        mocked_schedule_next_poll.assert_called_once_with(
            attempt_id=attempt.pk,
            poll_number=2,
        )

        self.assertEqual(
            result,
            "Transcription is in progress.",
        )

    # 7. COMPLETED сохраняет transcript

    @patch(
        "speaking.tasks."
        "load_transcription_result"
    )
    @patch(
        "speaking.tasks."
        "get_transcription_job"
    )
    def test_completed_saves_transcript(
        self,
        mocked_get_job,
        mocked_load_result,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt
                .Status
                .TRANSCRIBING
            )
        )

        mocked_get_job.return_value = {
            "status": "COMPLETED",
            "failure_reason": "",
        }

        mocked_load_result.return_value = {
            "results": {
                "transcripts": [
                    {
                        "transcript": (
                            "Hello this is my answer"
                        )
                    }
                ],
                "items": [
                    {
                        "type": "pronunciation",
                        "end_time": "2.50",
                    },
                    {
                        "type": "pronunciation",
                        "end_time": "5.00",
                    },
                ],
            }
        }

        poll_speaking_transcription.run(
            attempt.pk,
            0,
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.transcript,
            "Hello this is my answer",
        )

        self.assertEqual(
            attempt.status,
            SpeakingAttempt.Status.ANALYZING,
        )

    # 8. Рассчитываются duration,
    # words, WPM и fillers

    def test_speech_metrics_are_calculated(
        self,
    ):
        metrics = (
            calculate_speech_metrics(
                transcript=(
                    "Um I mean this is "
                    "my short answer"
                ),
                duration_seconds=30,
            )
        )

        self.assertEqual(
            metrics.duration_seconds,
            30,
        )

        self.assertEqual(
            metrics.word_count,
            8,
        )

        self.assertEqual(
            metrics.words_per_minute,
            16,
        )

        self.assertEqual(
            metrics.filler_word_count,
            2,
        )

    # 9. FAILED сохраняет
    # безопасную ошибку

    @patch(
        "speaking.tasks."
        "get_transcription_job"
    )
    def test_failed_transcription_saves_safe_error(
        self,
        mocked_get_job,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt
                .Status
                .TRANSCRIBING
            )
        )

        mocked_get_job.return_value = {
            "status": "FAILED",
            "failure_reason": (
                "Internal AWS technical "
                "failure information."
            ),
        }

        poll_speaking_transcription.run(
            attempt.pk,
            0,
        )

        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            SpeakingAttempt.Status.FAILED,
        )

        self.assertEqual(
            attempt.error_code,
            "transcription_failed",
        )

        self.assertEqual(
            attempt.error_message,
            (
                "Could not transcribe "
                "the recording."
            ),
        )

        self.assertNotIn(
            "Internal AWS",
            attempt.error_message,
        )

    # 10. detail возвращает comparison

    def test_detail_returns_comparison(
        self,
    ):
        previous_attempt = (
            self.create_attempt(
                attempt_number=1,
                attempt_status=(
                    SpeakingAttempt
                    .Status
                    .ANALYZING
                ),
            )
        )

        previous_attempt.duration_seconds = 60
        previous_attempt.word_count = 100
        previous_attempt.words_per_minute = 100
        previous_attempt.filler_word_count = 5

        previous_attempt.save(
            update_fields=[
                "duration_seconds",
                "word_count",
                "words_per_minute",
                "filler_word_count",
            ]
        )

        current_attempt = (
            self.create_attempt(
                attempt_number=2,
                attempt_status=(
                    SpeakingAttempt
                    .Status
                    .ANALYZING
                ),
            )
        )

        current_attempt.duration_seconds = 50
        current_attempt.word_count = 100
        current_attempt.words_per_minute = 120
        current_attempt.filler_word_count = 2

        current_attempt.save(
            update_fields=[
                "duration_seconds",
                "word_count",
                "words_per_minute",
                "filler_word_count",
            ]
        )

        response = self.client.get(
            (
                "/api/speaking-attempts/"
                f"{current_attempt.public_id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comparison = (
            response.data["comparison"]
        )

        self.assertEqual(
            comparison[
                "previous_attempt_number"
            ],
            1,
        )

        self.assertEqual(
            float(
                comparison[
                    "duration_delta_seconds"
                ]
            ),
            -10,
        )

        self.assertEqual(
            float(
                comparison[
                    "words_per_minute_delta"
                ]
            ),
            20,
        )

        self.assertEqual(
            comparison[
                "filler_word_count_delta"
            ],
            -3,
        )