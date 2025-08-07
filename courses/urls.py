from rest_framework.routers import SimpleRouter
from courses.apps import CoursesConfig
from courses.views import CourseViewSet, LessonViewSet

app_name = CoursesConfig.name  # "courses"

router = SimpleRouter()
router.register(r"courses", CourseViewSet, basename="courses")
router.register(r"lessons", LessonViewSet, basename="lessons")

urlpatterns = router.urls
