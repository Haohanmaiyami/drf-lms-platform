from rest_framework import serializers
from courses.validators import validate_youtube_url
from courses.models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    video = serializers.URLField(
        required=False,
        allow_null=True,
        allow_blank=True,
        validators=[validate_youtube_url],
    )
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "name",
            "course",
            "description",
            "preview",
            "preview_url",
            "video",
            "owner",
        )

    def get_preview_url(self, obj):
        request = self.context.get("request")
        if obj.preview:
            url = obj.preview.url
            return request.build_absolute_uri(url) if request else url
        return None


class CourseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    lessons_count = serializers.SerializerMethodField()
    lessons = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "name",
            "description",
            "preview",
            "preview_url",
            "owner",
            "lessons_count",
            "lessons",
            "is_subscribed",
        )

    def get_lessons_count(self, obj):
        return obj.lesson_set.count()

    def get_lessons(self, obj):
        from courses.permissions import has_course_access

        request = self.context.get("request")
        if not request:
            return []

        if not has_course_access(request.user, obj):
            return []

        lessons = obj.lesson_set.all()
        return LessonSerializer(lessons, many=True, context=self.context).data

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if not (request and request.user and request.user.is_authenticated):
            return False
        return obj.subscriptions.filter(user=request.user).exists()

    def get_preview_url(self, obj):
        request = self.context.get("request")
        if obj.preview:
            url = obj.preview.url
            return request.build_absolute_uri(url) if request else url
        return None