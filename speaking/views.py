from django.db.models import (
    Max,
    Prefetch,
    Q,
)
from django.shortcuts import (
    get_object_or_404,
)
from drf_yasg import openapi
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
from speaking.tasks import (
    process_speaking_attempt,
)
from speaking.permissions import (
    has_lesson_access,
)
from speaking.serializers import (
    SpeakingAttemptCompleteResponseSerializer,
    SpeakingAttemptCreateResponseSerializer,
    SpeakingAttemptCreateSerializer,
    SpeakingAttemptDetailSerializer,
    SpeakingAttemptHistoryPageSerializer,
    SpeakingAttemptHistorySerializer,
    SpeakingHistoryLessonSerializer,
    SpeakingHistoryPageSerializer,
    SpeakingStatsSerializer,
)
from speaking.services.uploads import (
    UploadNotFoundError,
    UploadStorageUnavailableError,
    UploadValidationError,
    complete_attempt_upload,
    prepare_attempt_upload,
)


from speaking.services.analytics import (
    build_speaking_stats,
)


SPEAKING_SWAGGER_TAGS = [
    "Speaking",
]


PAGE_PARAMETER = openapi.Parameter(
    name="page",
    in_=openapi.IN_QUERY,
    description="Page number.",
    type=openapi.TYPE_INTEGER,
    required=False,
)


PAGE_SIZE_PARAMETER = openapi.Parameter(
    name="page_size",
    in_=openapi.IN_QUERY,
    description=(
        "Attempts per page. "
        "Default: 20. Maximum: 100."
    ),
    type=openapi.TYPE_INTEGER,
    required=False,
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

class SpeakingHistoryAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    @swagger_auto_schema(
        operation_summary=(
            "Get all speaking history"
        ),
        operation_description=(
            "Returns the authenticated "
            "user's attempts grouped by "
            "lesson."
        ),
        manual_parameters=[
            PAGE_PARAMETER,
            PAGE_SIZE_PARAMETER,
        ],
        responses={
            200: (
                SpeakingHistoryPageSerializer
            ),
        },
        tags=SPEAKING_SWAGGER_TAGS,
    )
    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        user_attempts = (
            SpeakingAttempt.objects
            .filter(
                user=request.user,
            )
            .select_related(
                "feedback",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        lessons = (
            Lesson.objects
            .filter(
                speaking_attempts__user=(
                    request.user
                ),
            )
            .annotate(
                latest_attempt_at=Max(
                    (
                        "speaking_attempts"
                        "__created_at"
                    ),
                    filter=Q(
                        speaking_attempts__user=(
                            request.user
                        ),
                    ),
                ),
            )
            .prefetch_related(
                Prefetch(
                    "speaking_attempts",
                    queryset=user_attempts,
                    to_attr=(
                        "user_speaking_attempts"
                    ),
                ),
            )
            .distinct()
            .order_by(
                "-latest_attempt_at",
                "-id",
            )
        )

        paginator = (
            SpeakingAttemptPagination()
        )

        page = (
            paginator.paginate_queryset(
                lessons,
                request,
                view=self,
            )
        )

        serializer = (
            SpeakingHistoryLessonSerializer(
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


class SpeakingStatsAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    @swagger_auto_schema(
        operation_summary=(
            "Get speaking statistics"
        ),
        operation_description=(
            "Returns summary, level progress "
            "and activity for the current week."
        ),
        responses={
            200: SpeakingStatsSerializer,
        },
        tags=SPEAKING_SWAGGER_TAGS,
    )
    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        data = build_speaking_stats(
            request.user
        )

        serializer = (
            SpeakingStatsSerializer(
                data=data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        return Response(
            serializer.data
        )


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


    @swagger_auto_schema(
        operation_summary=(
            "List speaking attempts"
        ),
        operation_description=(
            "Returns only the authenticated "
            "user's attempts for the selected "
            "lesson. Results are ordered from "
            "newest to oldest."
        ),
        manual_parameters=[
            PAGE_PARAMETER,
            PAGE_SIZE_PARAMETER,
        ],
        responses={
            200: (
                SpeakingAttemptHistoryPageSerializer
            ),
            401: openapi.Response(
                description=(
                    "Authentication is required."
                ),
            ),
            404: openapi.Response(
                description=(
                    "Lesson was not found."
                ),
            ),
        },
        tags=SPEAKING_SWAGGER_TAGS,
    )

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
        operation_summary=(
            "Create a speaking attempt"
        ),
        operation_description=(
            "Creates a new SpeakingAttempt and "
            "returns a temporary presigned S3 "
            "PUT URL. Upload the raw audio file "
            "directly to upload.url using exactly "
            "the method and headers returned in "
            "the upload object. Do not send the "
            "JWT Authorization header to S3."
        ),
        request_body=(
            SpeakingAttemptCreateSerializer
        ),
        responses={
            201: (
                SpeakingAttemptCreateResponseSerializer
            ),
            400: openapi.Response(
                description=(
                    "Invalid content type, invalid "
                    "extension, or speaking is not "
                    "enabled for this lesson."
                ),
            ),
            401: openapi.Response(
                description=(
                    "Authentication is required."
                ),
            ),
            404: openapi.Response(
                description=(
                    "Lesson was not found."
                ),
            ),
            503: openapi.Response(
                description=(
                    "Audio storage is temporarily "
                    "unavailable."
                ),
            ),
        },
        tags=SPEAKING_SWAGGER_TAGS,
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
        operation_summary=(
            "Confirm audio upload"
        ),
        operation_description=(
            "Confirms that Flutter finished the "
            "direct S3 upload. The backend checks "
            "the S3 object, validates its size and "
            "content type, saves upload metadata, "
            "and starts the asynchronous processing "
            "pipeline. This endpoint is idempotent."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},
        ),
        responses={
            200: (
                SpeakingAttemptCompleteResponseSerializer
            ),
            400: openapi.Response(
                description=(
                    "The file is missing, empty, "
                    "too large, or has the wrong "
                    "content type."
                ),
            ),
            401: openapi.Response(
                description=(
                    "Authentication is required."
                ),
            ),
            404: openapi.Response(
                description=(
                    "Attempt was not found or belongs "
                    "to another user."
                ),
            ),
            503: openapi.Response(
                description=(
                    "Audio storage is temporarily "
                    "unavailable."
                ),
            ),
        },
        tags=SPEAKING_SWAGGER_TAGS,
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
            attempt, upload_completed = (
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

        if upload_completed:
            (
                process_speaking_attempt
                .delay_on_commit(
                    attempt.pk
                )
            )

        response_serializer = (
            SpeakingAttemptCompleteResponseSerializer(
                {
                    "id": (
                        attempt.public_id
                    ),
                    "attempt_number": (
                        attempt.attempt_number
                    ),
                    "status": attempt.status,
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

    @swagger_auto_schema(
        operation_summary=(
            "Get speaking attempt status"
        ),
        operation_description=(
            "Returns the current processing status "
            "and available result. Flutter should "
            "poll this endpoint until status becomes "
            "completed or failed."
        ),
        responses={
            200: (
                SpeakingAttemptDetailSerializer
            ),
            401: openapi.Response(
                description=(
                    "Authentication is required."
                ),
            ),
            404: openapi.Response(
                description=(
                    "Attempt was not found or belongs "
                    "to another user."
                ),
            ),
        },
        tags=SPEAKING_SWAGGER_TAGS,
    )

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