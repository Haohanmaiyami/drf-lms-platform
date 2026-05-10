from django.contrib import admin
from .models import (
    Course,
    Lesson,
    Subscription,
    LessonProgress,
    Quiz,
    QuizQuestion,
    QuizAnswerOption,
    QuizAttempt,
    QuizAttemptAnswer,
)


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


class QuizAnswerOptionInline(admin.TabularInline):
    model = QuizAnswerOption
    extra = 4


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "text", "order")
    list_filter = ("quiz",)
    search_fields = ("text",)
    inlines = [QuizAnswerOptionInline]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "lesson", "is_active", "created_at")
    list_filter = ("is_active", "lesson")
    search_fields = ("title", "lesson__name")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "quiz",
        "score",
        "total_questions",
        "percent",
        "level",
        "created_at",
    )
    list_filter = ("quiz", "level", "created_at")
    search_fields = ("user__email", "quiz__title")


@admin.register(QuizAttemptAnswer)
class QuizAttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "selected_option", "is_correct")
    list_filter = ("is_correct",)
