import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from courses.models import Lesson


def validate_key_points(value):
    """Проверяет структуру ключевых мыслей урока."""

    if not isinstance(value, list) or not value:
        raise ValidationError(
            "Key points must be a non-empty list."
        )

    if not all(
        isinstance(item, str) and item.strip()
        for item in value
    ):
        raise ValidationError(
            "Every key point must be a non-empty string."
        )


SCORE_VALIDATORS = [
    MinValueValidator(0),
    MaxValueValidator(100),
]


class LessonSpeakingConfig(models.Model):
    """
    AI-конфигурация существующего Lesson.

    Через эту модель AI заранее знает,
    о чём говорится в видео урока.
    """

    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name="speaking_config",
        verbose_name="Урок",
    )

    source_transcript = models.TextField(
        verbose_name="Транскрипт материала",
    )

    reference_summary = models.TextField(
        verbose_name="Эталонный краткий пересказ",
    )

    key_points = models.JSONField(
        validators=[validate_key_points],
        verbose_name="Ключевые мысли",
        help_text=(
            'JSON-массив строк, например: '
            '["Main idea", "Important conclusion"]'
        ),
    )

    target_duration_seconds = models.PositiveIntegerField(
        default=60,
        validators=[
            MinValueValidator(15),
            MaxValueValidator(300),
        ],
        verbose_name="Целевая длительность, сек.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Настройка speaking-урока"
        verbose_name_plural = "Настройки speaking-уроков"

    def __str__(self):
        return f"Speaking: {self.lesson.name}"


class SpeakingAttempt(models.Model):
    """Одна запись-пересказ пользователя."""

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        UPLOADED = "uploaded", "Uploaded"
        TRANSCRIBING = "transcribing", "Transcribing"
        ANALYZING = "analyzing", "Analyzing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Публичный UUID",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="speaking_attempts",
        verbose_name="Пользователь",
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="speaking_attempts",
        verbose_name="Урок",
    )

    attempt_number = models.PositiveIntegerField(
        verbose_name="Номер попытки",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
        verbose_name="Статус",
    )

    # Заполняются после подключения S3
    audio_key = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="S3 key",
    )

    audio_content_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="MIME-тип аудио",
    )

    audio_size_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name="Размер аудио, байт",
    )

    # Заполняются после транскрипции
    transcript = models.TextField(
        blank=True,
        verbose_name="Транскрипт пользователя",
    )

    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Длительность, сек.",
    )

    word_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Количество слов",
    )

    words_per_minute = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Слов в минуту",
    )

    filler_word_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Количество слов-паразитов",
    )

    # error_message должен содержать безопасный текст для frontend
    error_code = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Код ошибки",
    )

    error_message = models.TextField(
        blank=True,
        verbose_name="Описание ошибки",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    uploaded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Speaking-попытка"
        verbose_name_plural = "Speaking-попытки"
        ordering = ["-created_at", "-id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "lesson",
                    "attempt_number",
                ],
                name=(
                    "unique_speaking_attempt_"
                    "number_per_user_lesson"
                ),
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "lesson",
                    "created_at",
                ],
                name="speak_user_lesson_created_idx",
            )
        ]

    def __str__(self):
        return (
            f"{self.user} — {self.lesson.name} — "
            f"attempt {self.attempt_number} "
            f"({self.status})"
        )


class SpeakingFeedback(models.Model):
    """Структурированный результат AI-анализа."""

    attempt = models.OneToOneField(
        SpeakingAttempt,
        on_delete=models.CASCADE,
        related_name="feedback",
        verbose_name="Попытка",
    )

    overall_score = models.PositiveSmallIntegerField(
        validators=SCORE_VALIDATORS,
    )

    meaning_score = models.PositiveSmallIntegerField(
        validators=SCORE_VALIDATORS,
    )

    compression_score = models.PositiveSmallIntegerField(
        validators=SCORE_VALIDATORS,
    )

    clarity_score = models.PositiveSmallIntegerField(
        validators=SCORE_VALIDATORS,
    )

    grammar_score = models.PositiveSmallIntegerField(
        validators=SCORE_VALIDATORS,
    )

    vocabulary_score = models.PositiveSmallIntegerField(
        validators=SCORE_VALIDATORS,
    )

    fluency_score = models.PositiveSmallIntegerField(
        validators=SCORE_VALIDATORS,
    )

    covered_key_points = models.JSONField(
        default=list,
    )

    missed_key_points = models.JSONField(
        default=list,
    )

    unnecessary_details = models.JSONField(
        default=list,
    )

    corrections = models.JSONField(
        default=list,
    )

    short_feedback = models.TextField()

    concise_version = models.TextField()

    next_goal = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Speaking-feedback"
        verbose_name_plural = "Speaking-feedback"

    def __str__(self):
        return f"Feedback for {self.attempt.public_id}"