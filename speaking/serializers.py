from rest_framework import serializers

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

    method = serializers.CharField()

    headers = serializers.DictField(
        child=serializers.CharField()
    )

    expires_in = (
        serializers.IntegerField()
    )


class SpeakingAttemptCreateResponseSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()

    lesson_id = serializers.UUIDField()

    attempt_number = (
        serializers.IntegerField()
    )

    status = serializers.CharField()

    upload = SpeakingUploadSerializer()


class SpeakingAttemptAudioSerializer(
    serializers.Serializer
):
    content_type = serializers.CharField()

    size_bytes = serializers.IntegerField()


class SpeakingAttemptCompleteResponseSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()

    attempt_number = (
        serializers.IntegerField()
    )

    status = serializers.CharField()

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
            "word_count": obj.word_count,
            "words_per_minute": (
                obj.words_per_minute
            ),
            "filler_word_count": (
                obj.filler_word_count
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