from django.conf import settings
from django.db import transaction
from django.utils import timezone

from speaking.models import SpeakingAttempt
from speaking.services.attempts import (
    create_speaking_attempt,
)
from speaking.services.storage import (
    AudioObjectNotFound,
    AudioStorageError,
    delete_audio_object,
    generate_presigned_upload,
    head_audio_object,
)


class UploadNotFoundError(Exception):
    """Flutter ещё не загрузил файл в S3."""


class UploadValidationError(Exception):
    """Объект не прошёл проверку."""


class UploadStorageUnavailableError(
    Exception
):
    """S3 временно недоступен."""


@transaction.atomic
def prepare_attempt_upload(
    *,
    user,
    lesson,
    content_type: str,
    file_extension: str,
):
    attempt = create_speaking_attempt(
        user=user,
        lesson=lesson,
        audio_content_type=content_type,
        file_extension=file_extension,
    )

    try:
        upload = generate_presigned_upload(
            key=attempt.audio_key,
            content_type=(
                attempt.audio_content_type
            ),
        )
    except AudioStorageError as exc:
        raise (
            UploadStorageUnavailableError
        ) from exc

    return attempt, upload


@transaction.atomic
def complete_attempt_upload(
    *,
    attempt,
):
    locked_attempt = (
        SpeakingAttempt.objects
        .select_for_update()
        .get(pk=attempt.pk)
    )

    idempotent_statuses = {
        SpeakingAttempt.Status.UPLOADED,
        SpeakingAttempt.Status.TRANSCRIBING,
        SpeakingAttempt.Status.ANALYZING,
        SpeakingAttempt.Status.COMPLETED,
    }

    if (
        locked_attempt.status
        in idempotent_statuses
    ):
        return locked_attempt, False

    if (
        locked_attempt.status
        != SpeakingAttempt.Status.CREATED
    ):
        raise UploadValidationError(
            "This attempt cannot "
            "accept an upload."
        )

    try:
        metadata = head_audio_object(
            key=locked_attempt.audio_key,
        )
    except AudioObjectNotFound as exc:
        raise UploadNotFoundError from exc
    except AudioStorageError as exc:
        raise (
            UploadStorageUnavailableError
        ) from exc

    size_bytes = metadata["size_bytes"]
    content_type = metadata[
        "content_type"
    ]

    if size_bytes <= 0:
        delete_audio_object(
            key=locked_attempt.audio_key,
        )

        raise UploadValidationError(
            "The uploaded audio "
            "file is empty."
        )

    if (
        size_bytes
        > settings
        .SPEAKING_MAX_AUDIO_SIZE_BYTES
    ):
        delete_audio_object(
            key=locked_attempt.audio_key,
        )

        raise UploadValidationError(
            "The uploaded audio "
            "file is too large."
        )

    if (
        content_type
        != locked_attempt
        .audio_content_type
    ):
        delete_audio_object(
            key=locked_attempt.audio_key,
        )

        raise UploadValidationError(
            "The uploaded audio "
            "content type is invalid."
        )

    locked_attempt.audio_size_bytes = (
        size_bytes
    )

    locked_attempt.status = (
        SpeakingAttempt.Status.UPLOADED
    )

    locked_attempt.uploaded_at = (
        timezone.now()
    )

    locked_attempt.save(
        update_fields=[
            "audio_size_bytes",
            "status",
            "uploaded_at",
        ]
    )

    return locked_attempt, True