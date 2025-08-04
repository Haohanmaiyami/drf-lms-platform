from django.db import models


class Course(models.Model):
    name = models.CharField(
        max_length=100, verbose_name="Имя курса", help_text="Укажите название курса"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Описание курса",
        help_text="Укажите описание курса",
    )
    preview = models.ImageField(
        upload_to="courses/previews/",
        blank=True,
        null=True,
        verbose_name="Превью",
        help_text="Загрузите превью курса(изображение)",
    )

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"


class Lesson(models.Model):
    name = models.CharField(
        max_length=100, verbose_name="Имя урока", help_text="Укажите название урока"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        verbose_name="Курс",
        help_text="Выберите курс",
        blank=True,
        null=True,
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Описание урока",
        help_text="Укажите описание урока",
    )
    preview = models.ImageField(
        upload_to="courses/previews/",
        blank=True,
        null=True,
        verbose_name="Превью",
        help_text="Загрузите превью урока(изображение)",
    )
    video = models.URLField(
        verbose_name="Ссылка на видео",
        help_text="Укажите ссылку на видео, типа ютуб",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
