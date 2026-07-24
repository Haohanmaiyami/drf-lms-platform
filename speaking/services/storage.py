import logging
from functools import lru_cache
from pathlib import PurePosixPath

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from django.conf import settings


"""
Сервис работы с Amazon S3.

Почему существует этот модуль?

Мы выносим всю работу с Amazon S3 в отдельный сервис. Благодаря этому
остальная часть проекта ничего не знает о boto3 и внутреннем устройстве AWS.

Весь backend обращается к S3 только через функции этого файла:
- создание клиента;
- генерация presigned URL;
- проверка существования объекта;
- удаление файлов;
- построение ключей (S3 object key).

Если в будущем потребуется заменить Amazon S3 на другой storage
(например, MinIO, Cloudflare R2 или Google Cloud Storage),
изменения будут сосредоточены только в этом модуле.
"""

logger = logging.getLogger(__name__)



class AudioObjectNotFound(Exception):
    """Аудиообъект отсутствует в S3."""


class AudioStorageError(Exception):
    """S3 недоступен или настроен некорректно."""


@lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        config=Config(
            signature_version="s3v4",
        ),
    )


def get_speaking_bucket() -> str:
    bucket = settings.AWS_S3_SPEAKING_BUCKET

    if not bucket:
        raise AudioStorageError(
            "AWS_S3_SPEAKING_BUCKET "
            "is not configured."
        )

    return bucket


def build_audio_key(
    *,
    lesson_public_id,
    attempt_public_id,
    file_extension: str,
) -> str:
    extension = (
        file_extension
        .lower()
        .lstrip(".")
    )

    if extension != "m4a":
        raise ValueError(
            "Unsupported audio extension."
        )

    return str(
        PurePosixPath("speaking")
        / str(lesson_public_id)
        / f"{attempt_public_id}.{extension}"
    )


def generate_presigned_upload(
    *,
    key: str,
    content_type: str,
) -> dict:
    try:
        url = (
            get_s3_client()
            .generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": (
                        get_speaking_bucket()
                    ),
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=(
                    settings
                    .AWS_S3_PRESIGNED_EXPIRES
                ),
                HttpMethod="PUT",
            )
        )
    except (
        BotoCoreError,
        ClientError,
    ) as exc:
        raise AudioStorageError(
            "Could not create a presigned "
            "upload URL."
        ) from exc

    return {
        "url": url,
        "method": "PUT",
        "headers": {
            "Content-Type": content_type,
        },
        "expires_in": (
            settings
            .AWS_S3_PRESIGNED_EXPIRES
        ),
    }


def head_audio_object(
    *,
    key: str,
) -> dict:
    try:
        response = (
            get_s3_client()
            .head_object(
                Bucket=get_speaking_bucket(),
                Key=key,
            )
        )
    except ClientError as exc:
        error_code = str(
            exc.response
            .get("Error", {})
            .get("Code", "")
        )

        http_status = (
            exc.response
            .get("ResponseMetadata", {})
            .get("HTTPStatusCode")
        )

        if (
            http_status == 404
            or error_code
            in {
                "404",
                "NoSuchKey",
                "NotFound",
            }
        ):
            raise AudioObjectNotFound(
                "Audio object was not found."
            ) from exc

        raise AudioStorageError(
            "Could not verify "
            "the uploaded audio."
        ) from exc

    except BotoCoreError as exc:
        raise AudioStorageError(
            "Could not verify "
            "the uploaded audio."
        ) from exc

    return {
        "size_bytes": int(
            response["ContentLength"]
        ),
        "content_type": response.get(
            "ContentType",
            "",
        ),
    }


def delete_audio_object(
    *,
    key: str,
) -> None:
    try:
        (
            get_s3_client()
            .delete_object(
                Bucket=get_speaking_bucket(),
                Key=key,
            )
        )
    except (
        BotoCoreError,
        ClientError,
    ):
        logger.exception(
            "Could not delete invalid "
            "speaking audio: %s",
            key,
        )