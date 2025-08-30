from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from courses.models import Course, Lesson, Subscription
from courses.paginators import DefaultPagination
from courses.serializers import CourseSerializer, LessonSerializer
from courses.permissions import IsModer, NotModer, IsOwner
from rest_framework.pagination import PageNumberPagination
from .tasks import send_course_update_email



class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = Course.objects.all()
        user = self.request.user
        if self.action == "retrieve":
            return qs
        if self.action == "list":
            if (
                user.is_authenticated
                and not user.groups.filter(name="moderators").exists()
            ):
                return qs.filter(owner=user)
            return qs
        return qs

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
    permission_classes = [IsAuthenticated]
    pagination_class = LessonPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Lesson.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Lesson.objects.none()

        return Lesson.objects.filter(owner=user)

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
        course = get_object_or_404(Course, pk=course_id)

        existing = Subscription.objects.filter(user=user, course=course)
        if existing.exists():
            existing.delete()
            return Response({"message": "подписка удалена"}, status=status.HTTP_200_OK)
        Subscription.objects.create(user=user, course=course)
        return Response(
            {"message": "подписка добавлена"}, status=status.HTTP_201_CREATED
        )


