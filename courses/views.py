from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from courses.models import (
    Course,
    Lesson,
    Subscription,
    LessonProgress,
    Quiz,
    QuizAttempt,
    QuizAttemptAnswer,
)
from courses.serializers import (
    CourseListSerializer,
    CourseDetailSerializer,
    LessonSerializer,
    QuizSerializer,
    QuizSubmitSerializer,
)
from courses.permissions import IsModer, NotModer, IsOwner, has_course_access
from rest_framework.pagination import PageNumberPagination
from .tasks import send_course_update_email
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema

class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return CourseListSerializer
        return CourseDetailSerializer
    lookup_field = "public_id"
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Course.objects.all()

    def get_permissions(self):
        # классы прав "по операциям"
        if self.action in ["list", "retrieve"]:
            perms = [IsAuthenticated]
        elif self.action == "create":
            perms = [IsAuthenticated, NotModer]  # модератор не создаёт
        elif self.action in ["update", "partial_update"]:
            perms = [IsAuthenticated, IsOwner | IsModer]  # владелец ИЛИ модератор
        elif self.action == "destroy":
            perms = [
                IsAuthenticated,
                IsOwner,
                NotModer,
            ]  # удалить может только владелец и только если не модератор
        else:
            perms = [IsAuthenticated]
        return [p() for p in perms]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)  # привязка владельца

    def perform_update(self, serializer):
        instance = serializer.save()
        # всегда шлём после обновления
        send_course_update_email.delay(instance.id)


class LessonPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class LessonViewSet(ModelViewSet):
    serializer_class = LessonSerializer
    lookup_field = "public_id"
    permission_classes = [IsAuthenticated]
    pagination_class = LessonPagination
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Lesson.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Lesson.objects.none()

        if user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()

        return Lesson.objects.filter(
            course__subscriptions__user=user
        ) | Lesson.objects.filter(owner=user)

    def get_object(self):
        lesson = super().get_object()

        if self.action in ["retrieve"] and not has_course_access(
                self.request.user, lesson.course
        ):
            raise PermissionDenied("Subscribe to access this lesson.")

        return lesson

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            perms = [IsAuthenticated]
        elif self.action == "create":
            perms = [IsAuthenticated, NotModer]
        elif self.action in ["update", "partial_update"]:
            perms = [IsAuthenticated, IsOwner | IsModer]
        elif self.action == "destroy":
            perms = [IsAuthenticated, IsOwner, NotModer]
        else:
            perms = [IsAuthenticated]
        return [p() for p in perms]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get("course_id")
        course = get_object_or_404(Course, public_id=course_id)

        existing = Subscription.objects.filter(user=user, course=course)
        if existing.exists():
            existing.delete()
            return Response({"message": "подписка удалена"}, status=status.HTTP_200_OK)
        Subscription.objects.create(user=user, course=course)
        return Response(
            {"message": "подписка добавлена"}, status=status.HTTP_201_CREATED
        )

class LessonCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id, *args, **kwargs):
        lesson = get_object_or_404(Lesson, public_id=lesson_id)

        if not has_course_access(request.user, lesson.course):
            raise PermissionDenied("Subscribe to access this lesson.")

        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
        )

        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()

        return Response(
            {
                "lesson_id": str(lesson.public_id),
                "is_completed": True,
                "message": "урок отмечен как пройденный",
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, lesson_id, *args, **kwargs):
        lesson = get_object_or_404(Lesson, public_id=lesson_id)

        progress = LessonProgress.objects.filter(
            user=request.user,
            lesson=lesson,
        ).first()

        if progress:
            progress.is_completed = False
            progress.completed_at = None
            progress.save()

        return Response(
            {
                "lesson_id": str(lesson.public_id),
                "is_completed": False,
                "message": "отметка о прохождении снята",
            },
            status=status.HTTP_200_OK,
        )

def get_english_level(percent):
    if percent < 40:
        return "A2"
    if percent < 60:
        return "B1"
    if percent < 80:
        return "B2"
    return "C1"


class LessonQuizAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id, *args, **kwargs):
        lesson = get_object_or_404(Lesson, public_id=lesson_id)

        if not has_course_access(request.user, lesson.course):
            raise PermissionDenied("Subscribe to access this lesson.")

        quiz = get_object_or_404(
            Quiz.objects.prefetch_related("questions__options"),
            lesson=lesson,
            is_active=True,
        )

        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuizSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=QuizSubmitSerializer)

    def post(self, request, quiz_id, *args, **kwargs):
        quiz = get_object_or_404(
            Quiz.objects.prefetch_related("questions__options"),
            public_id=quiz_id,
            is_active=True,
        )

        if not has_course_access(request.user, quiz.lesson.course):
            raise PermissionDenied("Subscribe to access this quiz.")

        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submitted_answers = serializer.validated_data["answers"]
        answers_map = {
            str(item["question_id"]): str(item["option_id"])
            for item in submitted_answers
        }

        questions = list(quiz.questions.all())
        total_questions = len(questions)
        score = 0
        result_answers = []

        with transaction.atomic():
            attempt = QuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                total_questions=total_questions,
            )

            for question in questions:
                selected_option_id = answers_map.get(str(question.public_id))
                selected_option = None
                is_correct = False

                if selected_option_id:
                    selected_option = question.options.filter(
                        public_id=selected_option_id
                    ).first()

                    if selected_option and selected_option.is_correct:
                        is_correct = True
                        score += 1

                QuizAttemptAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_option=selected_option,
                    is_correct=is_correct,
                )

                correct_option = question.options.filter(is_correct=True).first()

                result_answers.append(
                    {
                        "question_id": str(question.public_id),
                        "question": question.text,
                        "selected_option_id": (
                            str(selected_option.public_id)
                            if selected_option
                            else None
                        ),
                        "selected_option": selected_option.text if selected_option else None,
                        "correct_option": correct_option.text if correct_option else None,
                        "is_correct": is_correct,
                        "explanation": question.explanation,
                    }
                )

            percent = round((score / total_questions) * 100) if total_questions else 0
            level = get_english_level(percent)

            attempt.score = score
            attempt.percent = percent
            attempt.level = level
            attempt.save()

        return Response(
            {
                "quiz_id": str(quiz.public_id),
                "score": score,
                "total_questions": total_questions,
                "percent": percent,
                "level": level,
                "answers": result_answers,
            },
            status=status.HTTP_200_OK,
        )