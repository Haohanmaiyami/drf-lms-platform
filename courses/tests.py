from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course, Lesson, Subscription

User = get_user_model()


# фабрики
def create_user(email, password="pass12345"):
    return User.objects.create_user(email=email, password=password)


def create_course(owner, name="DRF Course"):
    return Course.objects.create(name=name, owner=owner)


def create_lesson(owner, course, name="Lesson X", video=None):
    return Lesson.objects.create(name=name, course=course, video=video, owner=owner)


# CRUD уроков
class LessonCRUDTests(APITestCase):
    def setUp(self):
        self.owner = create_user("owner@test.com")
        self.other = create_user("other@test.com")
        self.course = create_course(self.owner, "Course A")

    def test_owner_can_create_retrieve_update_delete_lesson(self):
        self.client.force_authenticate(self.owner)
        # CREATE
        resp = self.client.post(
            "/api/lessons/",
            data={
                "name": "Intro",
                "course": self.course.id,
                "video": "https://youtu.be/dQw4w9WgXcQ",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        lesson_id = resp.data["id"]

        # RETRIEVE
        resp = self.client.get(f"/api/lessons/{lesson_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Intro")

        # UPDATE (PATCH)
        resp = self.client.patch(f"/api/lessons/{lesson_id}/", data={"name": "Intro 2"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Intro 2")

        # DELETE
        resp = self.client.delete(f"/api/lessons/{lesson_id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_user_cannot_update_or_delete_owners_lesson(self):
        # Создаёт владелец
        self.client.force_authenticate(self.owner)
        lesson = create_lesson(self.owner, self.course, "Only mine")
        # Пытается другой пользователь
        self.client.force_authenticate(self.other)
        resp = self.client.patch(f"/api/lessons/{lesson.id}/", data={"name": "Hack"})
        self.assertIn(
            resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )
        resp = self.client.delete(f"/api/lessons/{lesson.id}/")
        self.assertIn(
            resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )

    def test_create_rejects_non_youtube_video(self):
        self.client.force_authenticate(self.owner)
        resp = self.client.post(
            "/api/lessons/",
            data={
                "name": "Bad URL",
                "course": self.course.id,
                "video": "https://vimeo.com/123456",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("video", resp.data)


# Подписка
class SubscriptionTests(APITestCase):
    def setUp(self):
        self.user = create_user("user@test.com")
        self.owner = create_user("owner@test.com")
        self.course = create_course(self.owner, "Course B")

    def test_toggle_subscription(self):
        self.client.force_authenticate(self.user)

        # 1) Подписка (добавление)
        resp = self.client.post(
            "/api/courses/subscribe/", data={"course_id": self.course.id}
        )
        self.assertIn(resp.status_code, (status.HTTP_201_CREATED, status.HTTP_200_OK))
        self.assertTrue(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )
        self.assertIn("подписка", resp.data["message"])

        # 2) Повторный пост — отписка
        resp = self.client.post(
            "/api/courses/subscribe/", data={"course_id": self.course.id}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Subscription.objects.filter(user=self.user, course=self.course).exists()
        )
        self.assertIn("удалена", resp.data["message"])

    def test_course_detail_contains_is_subscribed(self):
        self.client.force_authenticate(self.user)
        Subscription.objects.create(user=self.user, course=self.course)
        resp = self.client.get(f"/api/courses/{self.course.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("is_subscribed", resp.data)
        self.assertTrue(resp.data["is_subscribed"])


# Пагинация
class PaginationTests(APITestCase):
    def setUp(self):
        self.owner = create_user("owner@test.com")
        self.course = create_course(self.owner, "Paginated Course")
        self.client.force_authenticate(self.owner)
        for i in range(7):
            create_lesson(self.owner, self.course, f"Lesson {i+1}")

        # ещё несколько курсов для проверки пагинации курсов
        for i in range(6):
            create_course(self.owner, f"Course #{i+1}")

    def test_lessons_list_pagination(self):
        resp = self.client.get("/api/lessons/?page=2&page_size=3")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("results", resp.data)
        self.assertEqual(resp.data["count"], 7)
        self.assertEqual(len(resp.data["results"]), 3)

    def test_courses_list_pagination(self):
        resp = self.client.get("/api/courses/?page=2&page_size=3")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("results", resp.data)
        # у нас 1 «Paginated Course» + 6 созданных = 7
        self.assertGreaterEqual(resp.data["count"], 7)
        self.assertEqual(len(resp.data["results"]), 3)
