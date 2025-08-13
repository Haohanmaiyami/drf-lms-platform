from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from courses.models import Course, Lesson
from courses.serializers import CourseSerializer, LessonSerializer
from courses.permissions import IsModer, NotModer, IsOwner

class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.groups.filter(name='moderators').exists():
            return Course.objects.all()               # модератор видит всё
        return Course.objects.filter(owner=user)      # остальные — только свои

    def get_permissions(self):
        # классы прав "по операциям"
        if self.action in ['list', 'retrieve']:
            perms = [IsAuthenticated]
        elif self.action == 'create':
            perms = [IsAuthenticated, NotModer]              # модератор не создаёт
        elif self.action in ['update', 'partial_update']:
            perms = [IsAuthenticated, IsOwner | IsModer]     # владелец ИЛИ модератор
        elif self.action == 'destroy':
            perms = [IsAuthenticated, IsOwner, NotModer]     # удалить может только владелец и только если не модератор
        else:
            perms = [IsAuthenticated]
        return [p() for p in perms]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)             # привязка владельца

class LessonViewSet(ModelViewSet):
    queryset = Lesson.objects.select_related('course').all()
    serializer_class = LessonSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.groups.filter(name='moderators').exists():
            return Lesson.objects.select_related('course').all()
        return Lesson.objects.filter(owner=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            perms = [IsAuthenticated]
        elif self.action == 'create':
            perms = [IsAuthenticated, NotModer]
        elif self.action in ['update', 'partial_update']:
            perms = [IsAuthenticated, IsOwner | IsModer]
        elif self.action == 'destroy':
            perms = [IsAuthenticated, IsOwner, NotModer]
        else:
            perms = [IsAuthenticated]
        return [p() for p in perms]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
