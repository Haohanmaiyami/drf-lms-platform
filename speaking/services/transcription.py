import json
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from django.conf import settings

from speaking.services.storage import (
    get_s3_client,
    get_speaking_bucket,
)


class TranscriptionServiceError(Exception):
    """
    Amazon Transcribe или S3
    временно недоступны.
    """


class TranscriptionResultNotFound(Exception):
    """
    Amazon Transcribe ещё не записал
    JSON-результат в S3.
    """


class InvalidTranscriptionResult(Exception):
    """
    Amazon Transcribe вернул
    неполный или неправильный JSON.
    """


@lru_cache(maxsize=1)
def get_transcribe_client():
    return boto3.client(
        "transcribe",
        region_name=settings.AWS_REGION,
        config=Config(
            retries={
                "max_attempts": 3,
                "mode": "standard",
            }
        ),
    )


def build_transcription_job_name(
    attempt_public_id,
) -> str:
    return (
        f"lingloop-{attempt_public_id}"
    )


def build_transcription_output_key(
    *,
    lesson_public_id,
    attempt_public_id,
) -> str:
    prefix = (
        settings
        .AWS_TRANSCRIBE_OUTPUT_PREFIX
        .strip("/")
    )

    filename = (
        f"{attempt_public_id}.json"
    )

    path = (
        f"{lesson_public_id}/"
        f"{filename}"
    )

    if not prefix:
        return path

    return f"{prefix}/{path}"


def build_media_uri(
    audio_key: str,
) -> str:
    return (
        f"s3://{get_speaking_bucket()}/"
        f"{audio_key}"
    )


def start_transcription_job(
    *,
    attempt,
) -> dict:
    job_name = (
        build_transcription_job_name(
            attempt.public_id
        )
    )

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
        (
            get_transcribe_client()
            .start_transcription_job(
                TranscriptionJobName=(
                    job_name
                ),
                LanguageCode=(
                    settings
                    .AWS_TRANSCRIBE_LANGUAGE_CODE
                ),
                MediaFormat="m4a",
                Media={
                    "MediaFileUri": (
                        build_media_uri(
                            attempt.audio_key
                        )
                    )
                },
                OutputBucketName=(
                    get_speaking_bucket()
                ),
                OutputKey=output_key,
            )
        )

    except ClientError as exc:
        error_code = str(
            exc.response
            .get("Error", {})
            .get("Code", "")
        )

        # Job name строится из attempt UUID.
        # Повторная Celery task может увидеть
        # уже существующий job — это нормально.
        if (
            error_code
            != "ConflictException"
        ):
            raise TranscriptionServiceError(
                "Could not start "
                "transcription job."
            ) from exc

    except BotoCoreError as exc:
        raise TranscriptionServiceError(
            "Could not start "
            "transcription job."
        ) from exc

    return {
        "job_name": job_name,
        "output_key": output_key,
    }


def get_transcription_job(
    *,
    job_name: str,
) -> dict:
    try:
        response = (
            get_transcribe_client()
            .get_transcription_job(
                TranscriptionJobName=(
                    job_name
                ),
            )
        )

    except (
        BotoCoreError,
        ClientError,
    ) as exc:
        raise TranscriptionServiceError(
            "Could not read "
            "transcription job."
        ) from exc

    job = response[
        "TranscriptionJob"
    ]

    return {
        "status": (
            job[
                "TranscriptionJobStatus"
            ]
        ),
        "failure_reason": (
            job.get(
                "FailureReason",
                "",
            )
        ),
    }


def load_transcription_result(
    *,
    output_key: str,
) -> dict:
    try:
        response = (
            get_s3_client()
            .get_object(
                Bucket=(
                    get_speaking_bucket()
                ),
                Key=output_key,
            )
        )

    except ClientError as exc:
        error_code = str(
            exc.response
            .get("Error", {})
            .get("Code", "")
        )

        if error_code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }:
            raise (
                TranscriptionResultNotFound
            ) from exc

        raise TranscriptionServiceError(
            "Could not load "
            "transcription result."
        ) from exc

    except BotoCoreError as exc:
        raise TranscriptionServiceError(
            "Could not load "
            "transcription result."
        ) from exc

    try:
        raw_body = (
            response["Body"].read()
        )

        return json.loads(
            raw_body.decode("utf-8")
        )

    except (
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise InvalidTranscriptionResult(
            "Transcription result "
            "is invalid."
        ) from exc


def extract_transcription_data(
    payload: dict,
) -> dict:
    try:
        results = payload["results"]

        transcripts = results[
            "transcripts"
        ]

        transcript = (
            transcripts[0][
                "transcript"
            ]
            .strip()
        )

        items = results.get(
            "items",
            [],
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise InvalidTranscriptionResult(
            "Transcription result "
            "is incomplete."
        ) from exc

    if not transcript:
        raise InvalidTranscriptionResult(
            "Transcript is empty."
        )

    end_times = []

    for item in items:
        if (
            item.get("type")
            != "pronunciation"
        ):
            continue

        end_time = item.get(
            "end_time"
        )

        if end_time is None:
            continue

        try:
            end_times.append(
                float(end_time)
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

    if not end_times:
        raise InvalidTranscriptionResult(
            "Transcription duration "
            "is missing."
        )

    return {
        "transcript": transcript,
        "duration_seconds": max(
            end_times
        ),
    }