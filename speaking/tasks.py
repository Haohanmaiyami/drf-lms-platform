import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from speaking.models import (
    SpeakingAttempt,
    SpeakingFeedback,
)
from speaking.services.bedrock import (
    BedrockInvalidResponse,
    BedrockServiceError,
    generate_speaking_feedback,
)
from speaking.services.metrics import (
    calculate_speech_metrics,
)
from speaking.services.transcription import (
    InvalidTranscriptionResult,
    TranscriptionResultNotFound,
    TranscriptionServiceError,
    build_transcription_job_name,
    build_transcription_output_key,
    extract_transcription_data,
    get_transcription_job,
    load_transcription_result,
    start_transcription_job,
)


logger = logging.getLogger(__name__)


@transaction.atomic
def claim_attempt_for_transcription(
    attempt_id: int,
):
    attempt = (
        SpeakingAttempt.objects
        .select_for_update()
        .select_related("lesson")
        .filter(pk=attempt_id)
        .first()
    )

    if attempt is None:
        return None

    if (
        attempt.status
        == SpeakingAttempt.Status.UPLOADED
    ):
        attempt.status = (
            SpeakingAttempt
            .Status.TRANSCRIBING
        )

        attempt.error_code = ""
        attempt.error_message = ""

        attempt.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
            ]
        )

        return attempt

    if (
        attempt.status
        == SpeakingAttempt
        .Status.TRANSCRIBING
    ):
        return attempt

    return None


@transaction.atomic
def mark_attempt_failed(
    *,
    attempt_id: int,
    error_code: str,
    error_message: str,
) -> None:
    attempt = (
        SpeakingAttempt.objects
        .select_for_update()
        .filter(pk=attempt_id)
        .first()
    )

    if attempt is None:
        return

    if attempt.status not in {
        SpeakingAttempt.Status.UPLOADED,
        SpeakingAttempt.Status.TRANSCRIBING,
        SpeakingAttempt.Status.ANALYZING,
    }:
        return

    attempt.status = (
        SpeakingAttempt.Status.FAILED
    )

    attempt.error_code = error_code
    attempt.error_message = error_message

    attempt.save(
        update_fields=[
            "status",
            "error_code",
            "error_message",
        ]
    )


@transaction.atomic
def save_transcription_result(
    *,
    attempt_id: int,
    transcript: str,
    metrics,
) -> bool:
    attempt = (
        SpeakingAttempt.objects
        .select_for_update()
        .filter(pk=attempt_id)
        .first()
    )

    if attempt is None:
        return False

    if (
        attempt.status
        != SpeakingAttempt
        .Status.TRANSCRIBING
    ):
        return False

    attempt.transcript = transcript

    attempt.duration_seconds = (
        metrics.duration_seconds
    )

    attempt.word_count = (
        metrics.word_count
    )

    attempt.words_per_minute = (
        metrics.words_per_minute
    )

    attempt.filler_word_count = (
        metrics.filler_word_count
    )

    attempt.status = (
        SpeakingAttempt.Status.ANALYZING
    )

    attempt.error_code = ""
    attempt.error_message = ""

    attempt.save(
        update_fields=[
            "transcript",
            "duration_seconds",
            "word_count",
            "words_per_minute",
            "filler_word_count",
            "status",
            "error_code",
            "error_message",
        ]
    )

    return True


def schedule_next_poll(
    *,
    attempt_id: int,
    poll_number: int,
) -> bool:
    if (
        poll_number
        >= settings
        .AWS_TRANSCRIBE_MAX_POLLS
    ):
        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "transcription_timeout"
            ),
            error_message=(
                "Audio transcription "
                "took too long."
            ),
        )

        return False

    (
        poll_speaking_transcription
        .apply_async(
            args=[
                attempt_id,
                poll_number + 1,
            ],
            countdown=(
                settings
                .AWS_TRANSCRIBE_POLL_SECONDS
            ),
        )
    )

    return True


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def process_speaking_attempt(
    self,
    attempt_id: int,
):
    attempt = (
        claim_attempt_for_transcription(
            attempt_id
        )
    )

    if attempt is None:
        return "Attempt skipped."

    try:
        job = start_transcription_job(
            attempt=attempt,
        )

    except TranscriptionServiceError as exc:
        logger.exception(
            "Could not start transcription "
            "for attempt %s",
            attempt_id,
        )

        if (
            self.request.retries
            < self.max_retries
        ):
            raise self.retry(
                exc=exc
            )

        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "transcription_start_failed"
            ),
            error_message=(
                "Could not start "
                "audio transcription."
            ),
        )

        return "Attempt failed."

    (
        poll_speaking_transcription
        .apply_async(
            args=[
                attempt_id,
                0,
            ],
            countdown=(
                settings
                .AWS_TRANSCRIBE_POLL_SECONDS
            ),
        )
    )

    return (
        "Transcription started: "
        f"{job['job_name']}"
    )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def poll_speaking_transcription(
    self,
    attempt_id: int,
    poll_number: int = 0,
):
    attempt = (
        SpeakingAttempt.objects
        .select_related("lesson")
        .filter(pk=attempt_id)
        .first()
    )

    if attempt is None:
        return "Attempt not found."

    if (
        attempt.status
        != SpeakingAttempt
        .Status.TRANSCRIBING
    ):
        return "Attempt skipped."

    job_name = (
        build_transcription_job_name(
            attempt.public_id
        )
    )

    try:
        job = get_transcription_job(
            job_name=job_name,
        )

    except TranscriptionServiceError as exc:
        logger.exception(
            "Could not poll transcription "
            "for attempt %s",
            attempt_id,
        )

        if (
            self.request.retries
            < self.max_retries
        ):
            raise self.retry(
                exc=exc
            )

        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "transcription_poll_failed"
            ),
            error_message=(
                "Could not check "
                "audio transcription."
            ),
        )

        return "Attempt failed."

    job_status = job["status"]

    if job_status in {
        "QUEUED",
        "IN_PROGRESS",
    }:
        schedule_next_poll(
            attempt_id=attempt_id,
            poll_number=poll_number,
        )

        return (
            "Transcription is in progress."
        )

    if job_status == "FAILED":
        logger.error(
            "Amazon Transcribe failed "
            "for attempt %s: %s",
            attempt_id,
            job.get(
                "failure_reason",
                "",
            ),
        )

        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "transcription_failed"
            ),
            error_message=(
                "Could not transcribe "
                "the recording."
            ),
        )

        return "Attempt failed."

    if job_status != "COMPLETED":
        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "transcription_unknown_status"
            ),
            error_message=(
                "Could not transcribe "
                "the recording."
            ),
        )

        return "Attempt failed."

    output_key = (
        build_transcription_output_key(
            lesson_public_id=(
                attempt.lesson.public_id
            ),
            attempt_public_id=(
                attempt.public_id
            ),
        )
    )

    try:
        payload = (
            load_transcription_result(
                output_key=output_key,
            )
        )

        transcription_data = (
            extract_transcription_data(
                payload
            )
        )

        metrics = (
            calculate_speech_metrics(
                transcript=(
                    transcription_data[
                        "transcript"
                    ]
                ),
                duration_seconds=(
                    transcription_data[
                        "duration_seconds"
                    ]
                ),
            )
        )

    except TranscriptionResultNotFound:
        schedule_next_poll(
            attempt_id=attempt_id,
            poll_number=poll_number,
        )

        return (
            "Transcript file is not ready."
        )

    except TranscriptionServiceError as exc:
        logger.exception(
            "Could not load transcript "
            "for attempt %s",
            attempt_id,
        )

        if (
            self.request.retries
            < self.max_retries
        ):
            raise self.retry(
                exc=exc
            )

        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "transcript_load_failed"
            ),
            error_message=(
                "Could not load "
                "the transcription result."
            ),
        )

        return "Attempt failed."

    except (
        InvalidTranscriptionResult,
        ValueError,
    ):
        logger.exception(
            "Invalid transcript "
            "for attempt %s",
            attempt_id,
        )

        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code="empty_transcript",
            error_message=(
                "The recording did not "
                "contain recognizable speech."
            ),
        )

        return "Attempt failed."

    result_saved = save_transcription_result(
        attempt_id=attempt_id,
        transcript=(
            transcription_data[
                "transcript"
            ]
        ),
        metrics=metrics,
    )

    if result_saved:
        analyze_speaking_attempt.delay(
            attempt_id
        )

    return (
        "Transcript and metrics saved."
    )


@transaction.atomic
def get_attempt_for_analysis(
    attempt_id: int,
):
    attempt = (
        SpeakingAttempt.objects
        .select_for_update()
        .filter(pk=attempt_id)
        .first()
    )

    if attempt is None:
        return None

    if (
        attempt.status
        != SpeakingAttempt.Status.ANALYZING
    ):
        return None

    if (
        SpeakingFeedback.objects
        .filter(attempt=attempt)
        .exists()
    ):
        attempt.status = (
            SpeakingAttempt.Status.COMPLETED
        )

        if attempt.completed_at is None:
            attempt.completed_at = (
                timezone.now()
            )

        attempt.error_code = ""
        attempt.error_message = ""

        attempt.save(
            update_fields=[
                "status",
                "completed_at",
                "error_code",
                "error_message",
            ]
        )

        return None

    return attempt


@transaction.atomic
def save_feedback_result(
    *,
    attempt_id: int,
    feedback_payload,
) -> bool:
    attempt = (
        SpeakingAttempt.objects
        .select_for_update()
        .filter(pk=attempt_id)
        .first()
    )

    if attempt is None:
        return False

    if (
        attempt.status
        != SpeakingAttempt.Status.ANALYZING
    ):
        return False

    _, created = (
        SpeakingFeedback.objects
        .get_or_create(
            attempt=attempt,
            defaults=(
                feedback_payload
                .to_model_defaults()
            ),
        )
    )

    attempt.status = (
        SpeakingAttempt.Status.COMPLETED
    )
    attempt.completed_at = (
        timezone.now()
    )
    attempt.error_code = ""
    attempt.error_message = ""

    attempt.save(
        update_fields=[
            "status",
            "completed_at",
            "error_code",
            "error_message",
        ]
    )

    return created


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=20,
)
def analyze_speaking_attempt(
    self,
    attempt_id: int,
):
    attempt = get_attempt_for_analysis(
        attempt_id
    )

    if attempt is None:
        return "Attempt skipped."

    try:
        feedback_payload = (
            generate_speaking_feedback(
                attempt=attempt,
            )
        )

    except BedrockServiceError as exc:
        logger.exception(
            "Could not generate feedback "
            "for attempt %s",
            attempt_id,
        )

        if (
            self.request.retries
            < self.max_retries
        ):
            raise self.retry(
                exc=exc
            )

        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "analysis_service_failed"
            ),
            error_message=(
                "Could not analyze "
                "the recording."
            ),
        )

        return "Attempt failed."

    except BedrockInvalidResponse:
        logger.exception(
            "Invalid Bedrock response "
            "for attempt %s",
            attempt_id,
        )

        mark_attempt_failed(
            attempt_id=attempt_id,
            error_code=(
                "analysis_invalid_response"
            ),
            error_message=(
                "Could not create "
                "valid speaking feedback."
            ),
        )

        return "Attempt failed."

    feedback_created = (
        save_feedback_result(
            attempt_id=attempt_id,
            feedback_payload=(
                feedback_payload
            ),
        )
    )

    if not feedback_created:
        return "Feedback already exists."

    return "Speaking feedback saved."