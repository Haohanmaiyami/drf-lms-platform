from django.shortcuts import (
    get_object_or_404,
)
from drf_yasg.utils import (
    swagger_auto_schema,
)
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    ValidationError,
)
from rest_framework.pagination import (
    PageNumberPagination,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Lesson
from speaking.models import SpeakingAttempt
from speaking.permissions import (
    has_lesson_access,
)
from speaking.serializers import (
    SpeakingAttemptCompleteResponseSerializer,
    SpeakingAttemptCreateResponseSerializer,
    SpeakingAttemptCreateSerializer,
    SpeakingAttemptDetailSerializer,
    SpeakingAttemptHistorySerializer,
)
from speaking.services.uploads import (
    UploadNotFoundError,
    UploadStorageUnavailableError,
    UploadValidationError,
    complete_attempt_upload,
    prepare_attempt_upload,
)


class AudioStorageUnavailable(
    APIException
):
    status_code = (
        status.HTTP_503_SERVICE_UNAVAILABLE
    )

    default_detail = (
        "Audio storage is "
        "temporarily unavailable."
    )

    default_code = (
        "audio_storage_unavailable"
    )


class SpeakingAttemptPagination(
    PageNumberPagination
):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LessonSpeakingAttemptListCreateAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    def get_lesson(
        self,
        request,
        lesson_id,
    ):
        lesson = get_object_or_404(
            Lesson.objects.select_related(
                "course",
                "speaking_config",
            ),
            public_id=lesson_id,
        )

        if not has_lesson_access(
            request.user,
            lesson,
        ):
            raise PermissionDenied(
                "You do not have access "
                "to this lesson."
            )

        return lesson

    def get(
        self,
        request,
        lesson_id,
        *args,
        **kwargs,
    ):
        lesson = self.get_lesson(
            request,
            lesson_id,
        )

        attempts = (
            SpeakingAttempt.objects
            .filter(
                user=request.user,
                lesson=lesson,
            )
            .select_related(
                "lesson",
                "feedback",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        paginator = (
            SpeakingAttemptPagination()
        )

        page = (
            paginator.paginate_queryset(
                attempts,
                request,
                view=self,
            )
        )

        serializer = (
            SpeakingAttemptHistorySerializer(
                page,
                many=True,
            )
        )

        return (
            paginator
            .get_paginated_response(
                serializer.data
            )
        )

    @swagger_auto_schema(
        request_body=(
            SpeakingAttemptCreateSerializer
        ),
        responses={
            201: (
                SpeakingAttemptCreateResponseSerializer
            ),
        },
    )
    def post(
        self,
        request,
        lesson_id,
        *args,
        **kwargs,
    ):
        lesson = self.get_lesson(
            request,
            lesson_id,
        )

        if not hasattr(
            lesson,
            "speaking_config",
        ):
            raise ValidationError(
                {
                    "detail": (
                        "Speaking is not enabled "
                        "for this lesson."
                    )
                }
            )

        serializer = (
            SpeakingAttemptCreateSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            attempt, upload = (
                prepare_attempt_upload(
                    user=request.user,
                    lesson=lesson,
                    content_type=(
                        serializer
                        .validated_data[
                            "content_type"
                        ]
                    ),
                    file_extension=(
                        serializer
                        .validated_data[
                            "file_extension"
                        ]
                    ),
                )
            )
        except (
            UploadStorageUnavailableError
        ) as exc:
            raise (
                AudioStorageUnavailable()
            ) from exc

        response_serializer = (
            SpeakingAttemptCreateResponseSerializer(
                {
                    "id": (
                        attempt.public_id
                    ),
                    "lesson_id": (
                        lesson.public_id
                    ),
                    "attempt_number": (
                        attempt
                        .attempt_number
                    ),
                    "status": (
                        attempt.status
                    ),
                    "upload": upload,
                }
            )
        )

        return Response(
            response_serializer.data,
            status=(
                status.HTTP_201_CREATED
            ),
        )


class SpeakingAttemptCompleteUploadAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    @swagger_auto_schema(
        responses={
            200: (
                SpeakingAttemptCompleteResponseSerializer
            ),
        },
    )
    def post(
        self,
        request,
        attempt_id,
        *args,
        **kwargs,
    ):
        attempt = get_object_or_404(
            SpeakingAttempt,
            public_id=attempt_id,
            user=request.user,
        )

        try:
            attempt, _ = (
                complete_attempt_upload(
                    attempt=attempt,
                )
            )
        except UploadNotFoundError as exc:
            raise ValidationError(
                {
                    "detail": (
                        "The audio file has "
                        "not been uploaded yet."
                    )
                }
            ) from exc

        except UploadValidationError as exc:
            raise ValidationError(
                {
                    "detail": str(exc),
                }
            ) from exc

        except (
            UploadStorageUnavailableError
        ) as exc:
            raise (
                AudioStorageUnavailable()
            ) from exc

        response_serializer = (
            SpeakingAttemptCompleteResponseSerializer(
                {
                    "id": (
                        attempt.public_id
                    ),
                    "attempt_number": (
                        attempt
                        .attempt_number
                    ),
                    "status": (
                        attempt.status
                    ),
                    "audio": {
                        "content_type": (
                            attempt
                            .audio_content_type
                        ),
                        "size_bytes": (
                            attempt
                            .audio_size_bytes
                        ),
                    },
                    "uploaded_at": (
                        attempt.uploaded_at
                    ),
                }
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


class SpeakingAttemptDetailAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        attempt_id,
        *args,
        **kwargs,
    ):
        attempt = get_object_or_404(
            SpeakingAttempt.objects
            .select_related(
                "lesson",
                "feedback",
            ),
            public_id=attempt_id,
            user=request.user,
        )

        serializer = (
            SpeakingAttemptDetailSerializer(
                attempt
            )
        )

        return Response(
            serializer.data
        )