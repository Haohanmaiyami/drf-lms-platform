from django.contrib import admin
from .models import Course, Lesson, Subscription, LessonProgress


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner")
    list_filter = ("owner",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "course", "owner")
    list_filter = ("owner", "course")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "created_at")
    search_fields = ("user__email", "course__name")
    list_filter = ("course",)
    raw_id_fields = ("user", "course")

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "lesson", "is_completed", "completed_at")
    list_filter = ("is_completed", "completed_at")
    search_fields = ("user__email", "lesson__name")
    raw_id_fields = ("user", "lesson")