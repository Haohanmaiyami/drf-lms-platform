from rest_framework import serializers

from courses.models import Lesson
from speaking.models import (
    SpeakingAttempt,
    SpeakingFeedback,
)


class SpeakingAttemptCreateSerializer(
    serializers.Serializer
):
    content_type = (
        serializers.ChoiceField(
            choices=[
                "audio/mp4",
                "audio/m4a",
                "audio/x-m4a",
            ]
        )
    )

    file_extension = (
        serializers.ChoiceField(
            choices=["m4a"],
        )
    )


class SpeakingUploadSerializer(
    serializers.Serializer
):
    url = serializers.URLField()

    method = serializers.ChoiceField(
        choices=["PUT"],
    )

    headers = serializers.DictField(
        child=serializers.CharField()
    )

    expires_in = (
        serializers.IntegerField(
            min_value=1,
        )
    )


class SpeakingAttemptCreateResponseSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()

    lesson_id = serializers.UUIDField()

    attempt_number = (
        serializers.IntegerField(
            min_value=1,
        )
    )

    status = serializers.ChoiceField(
        choices=(
            SpeakingAttempt.Status.choices
        ),
    )

    upload = SpeakingUploadSerializer()


class SpeakingAttemptAudioSerializer(
    serializers.Serializer
):
    content_type = serializers.CharField()

    size_bytes = serializers.IntegerField(
        min_value=1,
    )


class SpeakingAttemptCompleteResponseSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()

    attempt_number = (
        serializers.IntegerField(
            min_value=1,
        )
    )

    status = serializers.ChoiceField(
        choices=(
            SpeakingAttempt.Status.choices
        ),
    )

    audio = (
        SpeakingAttemptAudioSerializer()
    )

    uploaded_at = (
        serializers.DateTimeField()
    )


class SpeakingFeedbackSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = SpeakingFeedback

        fields = (
            "overall_score",
            "meaning_score",
            "compression_score",
            "clarity_score",
            "grammar_score",
            "vocabulary_score",
            "fluency_score",
            "covered_key_points",
            "missed_key_points",
            "unnecessary_details",
            "corrections",
            "short_feedback",
            "concise_version",
            "next_goal",
        )


class SpeakingAttemptHistorySerializer(
    serializers.ModelSerializer
):
    id = serializers.UUIDField(
        source="public_id",
        read_only=True,
    )

    lesson_id = serializers.UUIDField(
        source="lesson.public_id",
        read_only=True,
    )

    overall_score = (
        serializers
        .SerializerMethodField()
    )

    class Meta:
        model = SpeakingAttempt

        fields = (
            "id",
            "lesson_id",
            "attempt_number",
            "status",
            "duration_seconds",
            "words_per_minute",
            "overall_score",
            "created_at",
            "completed_at",
        )

    def get_overall_score(
        self,
        obj,
    ):
        feedback = getattr(
            obj,
            "feedback",
            None,
        )

        if feedback is None:
            return None

        return feedback.overall_score


class SpeakingAttemptHistoryPageSerializer(
    serializers.Serializer
):
    count = serializers.IntegerField(
        min_value=0,
    )

    next = serializers.URLField(
        allow_null=True,
        required=False,
    )

    previous = serializers.URLField(
        allow_null=True,
        required=False,
    )

    results = (
        SpeakingAttemptHistorySerializer(
            many=True,
        )
    )


class SpeakingHistoryLessonSerializer(
    serializers.ModelSerializer
):
    id = serializers.UUIDField(
        source="public_id",
        read_only=True,
    )

    title = serializers.CharField(
        source="name",
        read_only=True,
    )

    latest_attempt_at = (
        serializers.DateTimeField(
            read_only=True,
        )
    )

    attempts = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = Lesson

        fields = (
            "id",
            "title",
            "level",
            "latest_attempt_at",
            "attempts",
        )

    def get_attempts(
        self,
        obj,
    ):
        attempts = getattr(
            obj,
            "user_speaking_attempts",
            [],
        )

        return (
            SpeakingAttemptHistorySerializer(
                attempts,
                many=True,
            ).data
        )


class SpeakingHistoryPageSerializer(
    serializers.Serializer
):
    count = serializers.IntegerField(
        min_value=0,
    )

    next = serializers.URLField(
        allow_null=True,
        required=False,
    )

    previous = serializers.URLField(
        allow_null=True,
        required=False,
    )

    results = (
        SpeakingHistoryLessonSerializer(
            many=True,
        )
    )


class SpeakingStatsSummarySerializer(
    serializers.Serializer
):
    day_streak = serializers.IntegerField(
        min_value=0,
    )

    total_minutes = serializers.IntegerField(
        min_value=0,
    )

    average_score = serializers.IntegerField(
        min_value=0,
        max_value=100,
    )

    completed_attempts = (
        serializers.IntegerField(
            min_value=0,
        )
    )

    completed_lessons = (
        serializers.IntegerField(
            min_value=0,
        )
    )


class SpeakingLevelProgressSerializer(
    serializers.Serializer
):
    current_level = serializers.CharField(
        allow_null=True,
    )

    next_level = serializers.CharField(
        allow_null=True,
    )

    completed_lessons = (
        serializers.IntegerField(
            min_value=0,
        )
    )

    total_lessons = serializers.IntegerField(
        min_value=0,
    )

    percent = serializers.IntegerField(
        min_value=0,
        max_value=100,
    )


class SpeakingWeekDaySerializer(
    serializers.Serializer
):
    date = serializers.DateField()

    completed_attempts = (
        serializers.IntegerField(
            min_value=0,
        )
    )

    minutes = serializers.IntegerField(
        min_value=0,
    )


class SpeakingStatsSerializer(
    serializers.Serializer
):
    summary = (
        SpeakingStatsSummarySerializer()
    )

    level_progress = (
        SpeakingLevelProgressSerializer()
    )

    week = SpeakingWeekDaySerializer(
        many=True,
    )


class SpeakingAttemptDetailSerializer(
    serializers.ModelSerializer
):
    id = serializers.UUIDField(
        source="public_id",
        read_only=True,
    )

    lesson_id = serializers.UUIDField(
        source="lesson.public_id",
        read_only=True,
    )

    metrics = (
        serializers
        .SerializerMethodField()
    )

    comparison = (
        serializers
        .SerializerMethodField()
    )

    feedback = (
        serializers
        .SerializerMethodField()
    )

    error = (
        serializers
        .SerializerMethodField()
    )

    class Meta:
        model = SpeakingAttempt

        fields = (
            "id",
            "lesson_id",
            "attempt_number",
            "status",
            "transcript",
            "metrics",
            "comparison",
            "feedback",
            "error",
            "created_at",
            "uploaded_at",
            "completed_at",
        )

    def get_metrics(
        self,
        obj,
    ):
        if obj.duration_seconds is None:
            return None

        return {
            "duration_seconds": (
                obj.duration_seconds
            ),
            "word_count": (
                obj.word_count
            ),
            "words_per_minute": (
                obj.words_per_minute
            ),
            "filler_word_count": (
                obj.filler_word_count
            ),
        }

    def get_comparison(
        self,
        obj,
    ):
        if obj.duration_seconds is None:
            return None

        previous_attempt = (
            SpeakingAttempt.objects
            .filter(
                user_id=obj.user_id,
                lesson_id=obj.lesson_id,
                attempt_number__lt=(
                    obj.attempt_number
                ),
                duration_seconds__isnull=False,
                words_per_minute__isnull=False,
                filler_word_count__isnull=False,
            )
            .order_by(
                "-attempt_number"
            )
            .first()
        )

        if previous_attempt is None:
            return None

        return {
            "previous_attempt_number": (
                previous_attempt
                .attempt_number
            ),
            "duration_delta_seconds": round(
                obj.duration_seconds
                - previous_attempt
                .duration_seconds,
                2,
            ),
            "words_per_minute_delta": round(
                obj.words_per_minute
                - previous_attempt
                .words_per_minute,
                2,
            ),
            "filler_word_count_delta": (
                obj.filler_word_count
                - previous_attempt
                .filler_word_count
            ),
        }

    def get_feedback(
        self,
        obj,
    ):
        feedback = getattr(
            obj,
            "feedback",
            None,
        )

        if feedback is None:
            return None

        return (
            SpeakingFeedbackSerializer(
                feedback,
            ).data
        )

    def get_error(
        self,
        obj,
    ):
        if (
            obj.status
            != SpeakingAttempt.Status.FAILED
        ):
            return None

        return {
            "code": (
                obj.error_code
                or "processing_failed"
            ),
            "message": (
                obj.error_message
                or (
                    "Could not process "
                    "the recording."
                )
            ),
        }