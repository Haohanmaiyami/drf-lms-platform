from rest_framework.serializers import ModelSerializer
from rest_framework import serializers


from courses.models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Lesson
        fields = "__all__"


class CourseSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    lessons_count = serializers.SerializerMethodField()
    # т к нет related name тогда придется lesson_set
    lessons = LessonSerializer(source="lesson_set", many=True, read_only=True)

    class Meta:
        model = Course
        fields = (
            "id", "name", "description", "preview",
            "owner", "lessons_count", "lessons",
        )

    def get_lessons_count(self, obj):
        return obj.lesson_set.count()



