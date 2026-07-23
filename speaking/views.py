from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Lesson
from speaking.models import SpeakingAttempt
from speaking.permissions import has_lesson_access
from speaking.serializers import (
    SpeakingAttemptDetailSerializer,
    SpeakingAttemptHistorySerializer,
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
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        lesson_id,
        *args,
        **kwargs,
    ):
        lesson = get_object_or_404(
            Lesson.objects.select_related("course"),
            public_id=lesson_id,
        )

        if not has_lesson_access(
            request.user,
            lesson,
        ):
            raise PermissionDenied(
                "You do not have access to this lesson."
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

        paginator = SpeakingAttemptPagination()

        page = paginator.paginate_queryset(
            attempts,
            request,
            view=self,
        )

        serializer = (
            SpeakingAttemptHistorySerializer(
                page,
                many=True,
            )
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    # POST будет добавлен на втором дне:
    # создаст attempt и вернёт presigned S3 URL.


class SpeakingAttemptDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        attempt_id,
        *args,
        **kwargs,
    ):
        attempt = get_object_or_404(
            SpeakingAttempt.objects.select_related(
                "lesson",
                "feedback",
            ),
            public_id=attempt_id,
            user=request.user,
        )

        serializer = SpeakingAttemptDetailSerializer(
            attempt
        )

        return Response(serializer.data)