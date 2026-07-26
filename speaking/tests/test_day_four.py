from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)
from django.test import (
    override_settings,
)
from pydantic import ValidationError
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
from speaking.services.bedrock import (
    BedrockInvalidResponse,
    extract_feedback_input,
    generate_speaking_feedback,
)
from speaking.services.feedback_prompt import (
    build_feedback_prompt,
)
from speaking.services.feedback_schema import (
    SpeakingFeedbackPayload,
)
from speaking.tasks import (
    analyze_speaking_attempt,
)


User = get_user_model()


@override_settings(
    AWS_BEDROCK_MODEL_ID=(
        "us.amazon.nova-2-lite-v1:0"
    ),
    AWS_BEDROCK_MAX_TOKENS=2500,
    AWS_BEDROCK_TEMPERATURE=0,
    AWS_BEDROCK_VALIDATION_RETRIES=1,
)
class SpeakingDayFourTests(
    APITestCase
):
    def setUp(self):
        self.owner = (
            User.objects.create_user(
                email=(
                    "owner-day-four@test.com"
                ),
                password="password123",
            )
        )

        self.student = (
            User.objects.create_user(
                email=(
                    "student-day-four@test.com"
                ),
                password="password123",
            )
        )

        self.course = (
            Course.objects.create(
                name=(
                    "Speaking Day Four Course"
                ),
                owner=self.owner,
            )
        )

        self.lesson = (
            Lesson.objects.create(
                name=(
                    "Ordering Coffee"
                ),
                course=self.course,
                owner=self.owner,
            )
        )

        self.speaking_config = (
            LessonSpeakingConfig
            .objects.create(
                lesson=self.lesson,
                source_transcript=(
                    "A customer enters a cafe, "
                    "orders a coffee, and chooses "
                    "a medium size."
                ),
                reference_summary=(
                    "The customer orders "
                    "a medium coffee."
                ),
                key_points=[
                    (
                        "The customer orders "
                        "a coffee"
                    ),
                    (
                        "The customer chooses "
                        "the size"
                    ),
                ],
                target_duration_seconds=45,
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
                SpeakingAttempt
                .Status
                .ANALYZING
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
                transcript=(
                    "The customer entered "
                    "the cafe and ordered "
                    "a medium coffee."
                ),
                duration_seconds=40.0,
                word_count=10,
                words_per_minute=15.0,
                filler_word_count=1,
            )
        )

    def valid_feedback_data(self):
        return {
            "overall_score": 84,
            "meaning_score": 90,
            "compression_score": 80,
            "clarity_score": 85,
            "grammar_score": 88,
            "vocabulary_score": 82,
            "fluency_score": 78,
            "covered_key_points": [
                (
                    "The customer orders "
                    "a coffee"
                ),
            ],
            "missed_key_points": [
                (
                    "The customer chooses "
                    "the size"
                ),
            ],
            "unnecessary_details": [],
            "corrections": [
                {
                    "original": (
                        "He order a coffee"
                    ),
                    "corrected": (
                        "He orders a coffee"
                    ),
                    "explanation": (
                        "Use -s with a "
                        "third-person singular verb."
                    ),
                }
            ],
            "short_feedback": (
                "You communicated the main "
                "idea clearly."
            ),
            "concise_version": (
                "The customer orders "
                "a medium coffee."
            ),
            "next_goal": (
                "Retell the story in "
                "45 seconds with no more "
                "than one filler word."
            ),
        }

    def valid_bedrock_response(
        self,
        *,
        feedback_data=None,
    ):
        if feedback_data is None:
            feedback_data = (
                self.valid_feedback_data()
            )

        return {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": (
                                    "tool-use-test-id"
                                ),
                                "name": (
                                    "submit_speaking_feedback"
                                ),
                                "input": feedback_data,
                            }
                        }
                    ],
                }
            },
            "stopReason": "tool_use",
        }

    # 1. Pydantic отклоняет score выше 100

    def test_feedback_schema_rejects_score_above_100(
        self,
    ):
        feedback_data = (
            self.valid_feedback_data()
        )

        feedback_data[
            "meaning_score"
        ] = 101

        with self.assertRaises(
            ValidationError
        ):
            (
                SpeakingFeedbackPayload
                .model_validate(
                    feedback_data
                )
            )

    # 2. Prompt содержит данные урока,
    # transcript и Python-метрики

    def test_feedback_prompt_contains_lesson_and_metrics(
        self,
    ):
        attempt = self.create_attempt()

        prompt = build_feedback_prompt(
            attempt
        )

        self.assertIn(
            self.speaking_config
            .source_transcript,
            prompt,
        )

        self.assertIn(
            self.speaking_config
            .reference_summary,
            prompt,
        )

        self.assertIn(
            attempt.transcript,
            prompt,
        )

        self.assertIn(
            '"target_duration_seconds": 45',
            prompt,
        )

        self.assertIn(
            '"duration_seconds": 40.0',
            prompt,
        )

        self.assertIn(
            '"word_count": 10',
            prompt,
        )

        self.assertIn(
            '"words_per_minute": 15.0',
            prompt,
        )

        self.assertIn(
            '"filler_word_count": 1',
            prompt,
        )

        self.assertIn(
            (
                '"target_duration_'
                'delta_seconds": -5.0'
            ),
            prompt,
        )

    # 3. Bedrock tool input корректно
    # извлекается и проходит Pydantic

    def test_bedrock_tool_input_is_validated(
        self,
    ):
        response = (
            self.valid_bedrock_response()
        )

        tool_input = (
            extract_feedback_input(
                response
            )
        )

        payload = (
            SpeakingFeedbackPayload
            .model_validate(
                tool_input
            )
        )

        self.assertEqual(
            payload.meaning_score,
            90,
        )

        self.assertEqual(
            payload.fluency_score,
            78,
        )

        self.assertEqual(
            payload.corrections[0]
            .corrected,
            "He orders a coffee",
        )

    # 4. Если первый ответ Bedrock
    # не проходит validation,
    # выполняется повторный запрос

    @patch(
        "speaking.services.bedrock."
        "request_feedback"
    )
    def test_invalid_bedrock_result_is_retried(
        self,
        mocked_request_feedback,
    ):
        attempt = self.create_attempt()

        invalid_data = (
            self.valid_feedback_data()
        )

        invalid_data[
            "overall_score"
        ] = 150

        mocked_request_feedback.side_effect = [
            self.valid_bedrock_response(
                feedback_data=invalid_data,
            ),
            self.valid_bedrock_response(),
        ]

        result = (
            generate_speaking_feedback(
                attempt=attempt
            )
        )

        self.assertEqual(
            mocked_request_feedback.call_count,
            2,
        )

        self.assertEqual(
            result.overall_score,
            84,
        )

    # 5. AI task сохраняет feedback
    # и переводит attempt в completed

    @patch(
        "speaking.tasks."
        "generate_speaking_feedback"
    )
    def test_analysis_task_saves_feedback_and_completes_attempt(
        self,
        mocked_generate_feedback,
    ):
        attempt = self.create_attempt()

        mocked_generate_feedback.return_value = (
            SpeakingFeedbackPayload
            .model_validate(
                self.valid_feedback_data()
            )
        )

        result = (
            analyze_speaking_attempt.run(
                attempt.pk
            )
        )

        attempt.refresh_from_db()

        self.assertEqual(
            result,
            "Speaking feedback saved.",
        )

        self.assertEqual(
            attempt.status,
            SpeakingAttempt
            .Status
            .COMPLETED,
        )

        self.assertIsNotNone(
            attempt.completed_at
        )

        self.assertTrue(
            SpeakingFeedback.objects.filter(
                attempt=attempt
            ).exists()
        )

        feedback = attempt.feedback

        self.assertEqual(
            feedback.meaning_score,
            90,
        )

        self.assertEqual(
            feedback.short_feedback,
            (
                "You communicated the main "
                "idea clearly."
            ),
        )

    # 6. overall_score пересчитывается
    # backend по фиксированной формуле

    @patch(
        "speaking.tasks."
        "generate_speaking_feedback"
    )
    def test_backend_calculates_weighted_overall_score(
        self,
        mocked_generate_feedback,
    ):
        attempt = self.create_attempt()

        feedback_data = (
            self.valid_feedback_data()
        )

        # Модель может прислать другое
        # overall, но backend его заменит.
        feedback_data[
            "overall_score"
        ] = 10

        mocked_generate_feedback.return_value = (
            SpeakingFeedbackPayload
            .model_validate(
                feedback_data
            )
        )

        analyze_speaking_attempt.run(
            attempt.pk
        )

        feedback = (
            SpeakingFeedback.objects.get(
                attempt=attempt
            )
        )

        # 90 * 0.30
        # + 80 * 0.15
        # + 85 * 0.15
        # + 88 * 0.10
        # + 82 * 0.10
        # + 78 * 0.20
        # = 84.35 → round() = 84
        self.assertEqual(
            feedback.overall_score,
            84,
        )

    # 7. Повторная task не создаёт
    # второй SpeakingFeedback

    @patch(
        "speaking.tasks."
        "generate_speaking_feedback"
    )
    def test_existing_feedback_is_not_duplicated(
        self,
        mocked_generate_feedback,
    ):
        attempt = self.create_attempt()

        payload = (
            SpeakingFeedbackPayload
            .model_validate(
                self.valid_feedback_data()
            )
        )

        SpeakingFeedback.objects.create(
            attempt=attempt,
            **payload.to_model_defaults(),
        )

        result = (
            analyze_speaking_attempt.run(
                attempt.pk
            )
        )

        attempt.refresh_from_db()

        self.assertEqual(
            result,
            "Attempt skipped.",
        )

        self.assertEqual(
            SpeakingFeedback.objects.filter(
                attempt=attempt
            ).count(),
            1,
        )

        self.assertEqual(
            attempt.status,
            SpeakingAttempt
            .Status
            .COMPLETED,
        )

        self.assertIsNotNone(
            attempt.completed_at
        )

        mocked_generate_feedback.assert_not_called()

    # 8. Неправильный AI-ответ
    # переводит attempt в failed

    @patch(
        "speaking.tasks."
        "generate_speaking_feedback"
    )
    def test_invalid_bedrock_response_marks_attempt_failed(
        self,
        mocked_generate_feedback,
    ):
        attempt = self.create_attempt()

        mocked_generate_feedback.side_effect = (
            BedrockInvalidResponse(
                "Invalid AI response."
            )
        )

        result = (
            analyze_speaking_attempt.run(
                attempt.pk
            )
        )

        attempt.refresh_from_db()

        self.assertEqual(
            result,
            "Attempt failed.",
        )

        self.assertEqual(
            attempt.status,
            SpeakingAttempt
            .Status
            .FAILED,
        )

        self.assertEqual(
            attempt.error_code,
            "analysis_invalid_response",
        )

        self.assertEqual(
            attempt.error_message,
            (
                "Could not create valid "
                "speaking feedback."
            ),
        )

        self.assertFalse(
            SpeakingFeedback.objects.filter(
                attempt=attempt
            ).exists()
        )

    # 9. Detail endpoint возвращает
    # сохранённый feedback

    def test_attempt_detail_returns_feedback(
        self,
    ):
        attempt = self.create_attempt(
            attempt_status=(
                SpeakingAttempt
                .Status
                .COMPLETED
            )
        )

        payload = (
            SpeakingFeedbackPayload
            .model_validate(
                self.valid_feedback_data()
            )
        )

        SpeakingFeedback.objects.create(
            attempt=attempt,
            **payload.to_model_defaults(),
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

        self.assertIsNotNone(
            response.data["feedback"]
        )

        self.assertEqual(
            response.data["feedback"][
                "overall_score"
            ],
            84,
        )

        self.assertEqual(
            response.data["feedback"][
                "meaning_score"
            ],
            90,
        )

        self.assertEqual(
            response.data["feedback"][
                "corrections"
            ][0]["corrected"],
            "He orders a coffee",
        )

        self.assertEqual(
            response.data["feedback"][
                "next_goal"
            ],
            (
                "Retell the story in "
                "45 seconds with no more "
                "than one filler word."
            ),
        )

    # 10. Ответ без нужного tool call
    # считается неправильным

    def test_missing_feedback_tool_is_rejected(
        self,
    ):
        response = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "text": (
                                "Here is some "
                                "unstructured feedback."
                            )
                        }
                    ],
                }
            }
        }

        with self.assertRaises(
            BedrockInvalidResponse
        ):
            extract_feedback_input(
                response
            )