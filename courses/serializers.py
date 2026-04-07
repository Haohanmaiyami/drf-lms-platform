from rest_framework import serializers
from courses.validators import validate_youtube_url
from courses.models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
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
        fields = "__all__"

    def get_preview_url(self, obj):
        request = self.context.get("request")
        if obj.preview:
            url = obj.preview.url
            return request.build_absolute_uri(url) if request else url
        return None


class CourseSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(source="lesson_set", many=True, read_only=True)
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