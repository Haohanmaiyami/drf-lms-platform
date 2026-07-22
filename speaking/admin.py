from django.contrib import admin

from speaking.models import (
    LessonSpeakingConfig,
    SpeakingAttempt,
    SpeakingFeedback,
)


@admin.register(LessonSpeakingConfig)
class LessonSpeakingConfigAdmin(
    admin.ModelAdmin
):
    list_display = (
        "id",
        "lesson",
        "target_duration_seconds",
        "updated_at",
    )

    search_fields = (
        "lesson__name",
        "lesson__course__name",
    )

    raw_id_fields = ("lesson",)


@admin.register(SpeakingAttempt)
class SpeakingAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "public_id",
        "user",
        "lesson",
        "attempt_number",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "public_id",
        "user__email",
        "lesson__name",
    )

    raw_id_fields = (
        "user",
        "lesson",
    )

    readonly_fields = (
        "public_id",
        "attempt_number",
        "status",
        "audio_key",
        "audio_content_type",
        "audio_size_bytes",
        "transcript",
        "duration_seconds",
        "word_count",
        "words_per_minute",
        "filler_word_count",
        "error_code",
        "error_message",
        "created_at",
        "uploaded_at",
        "completed_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(SpeakingFeedback)
class SpeakingFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "attempt",
        "overall_score",
        "created_at",
    )

    search_fields = (
        "attempt__public_id",
        "attempt__user__email",
    )

    raw_id_fields = ("attempt",)

    readonly_fields = [
        field.name
        for field in SpeakingFeedback._meta.fields
    ]

    def has_add_permission(self, request):
        return False