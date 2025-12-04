# DRF LMS Backend
Backend project for an online learning platform (LMS) built with Django REST Framework.  Includes courses, lessons, custom users, payments, subscriptions, permissions, API docs, async tasks and Docker setup.


### Core Features

- **Models**
  - Custom user: email login, phone, city, avatar.
  - **Course** and **Lesson** with one‑to‑many relation.
  - **Payment**: payment for a course or lesson (amount, method, date).
  - **Subscription**: user subscription to a course.

- **API (DRF)**
  - Full CRUD for courses (ViewSet) and lessons (generic views).
  - `CourseSerializer` returns `lessons_count` and nested list of lessons.
  - Pagination via page and `page_size` query params.

- **Auth & Permissions**
  - JWT authentication (token obtain & refresh).
  - All APIs are protected by default (`IsAuthenticated`).
  - Roles & permissions:
    - regular user — sees and manages only own objects;
    - moderator — can view and edit courses/lessons of other users;
    - ownership check via `IsOwner` + `owner` field on `Course` and `Lesson`.

- **Payments & Filtering**
  - `Payment` model with fixtures for test data.
  - `/api/payments/` endpoint with filters by course, lesson, payment method and ordering by date.
  - **Stripe** integration:
    - product & price creation;
    - Checkout Session creation;
    - storing payment URL in `Payment`.

- **Subscriptions & Validators**
  - Course subscriptions: `Subscription(user, course)` (unique pair).
  - Toggle endpoint to subscribe/unsubscribe, `is_subscribed` flag in `CourseSerializer`.
  - Video URL validator: only `youtube.com` / `youtu.be` are allowed; other domains return 400 for `video`.

- **Documentation & Security**
  - **drf-yasg** enabled: Swagger UI and ReDoc:
    - `http://localhost:8000/swagger/`
    - `http://localhost:8000/redoc/`
  - Main endpoints are documented in the OpenAPI schema.

- **Celery, Redis & Background Jobs**
  - **Celery worker** and **celery-beat** configured, Redis as broker.
  - Async email notifications to subscribers on course update (PATCH/PUT).
  - Periodic task to deactivate inactive users (cron via beat).
  - SMTP (Yandex Mail) used for sending emails.

- **Docker & Docker Compose**
  - `docker-compose` runs:
    - web (Django/DRF),
    - PostgreSQL,
    - Redis,
    - Celery worker,
    - Celery beat.
  - Example commands to run project and migrations:
    - `docker compose up -d --build`
    - `docker compose exec web python manage.py migrate`
    - `docker compose exec web python manage.py createsuperuser`

### Quick Start (local, without Docker)

```bash
git clone https://github.com/Haohanmaiyami/drf-proj.git
cd drf-proj
poetry install
cp .env.example .env   # fill DB, Redis, email, Stripe, etc.
python manage.py migrate
python manage.py runserver
```

Main URLs:

- Swagger: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`
- Admin: `http://localhost:8000/admin/`
- Sample API: `http://localhost:8000/api/courses/`

### Test Users

- Superuser: `admin@mail.ru` / `admin`
- Superuser (docker version): `admin2@mail.ru` / `admin`
- Regular user: `user1@example.com` / `Passw0rd!`
- Moderator: `user_regular@example.com` / `Passw0rd!`


------------------------------------------------------------------------
-------------
------------------------------------
-------------
------------------------------------
-------------
------------------------------------
-------------
------------------------------------
-------------

-------------


# 📚 DRF LMS Backend

Учебный backend-проект платформы онлайн-обучения (LMS) на Django REST Framework.  
Реализует курсы, уроки, пользователей, оплату, подписки, права доступа, документацию, асинхронные задачи и запуск через Docker.


## 🚀 Установка

```
git clone https://github.com/Haohanmaiyami/drf-proj.git
cd drf-proj
poetry install
```

## 🖥️ Запуск сервера

```
python manage.py runserver
```

## 🧪 Тестирование API

- Используйте Postman или другой HTTP-клиент
- Примеры эндпоинтов:
  - `GET /courses/`
  - `POST /courses/`
  - `GET /courses/lessons/`

## 🛠️ Стек технологий

- Python 3.13
- Django
- Django REST Framework
- PostgreSQL (если подключается)

## 📁 Структура проекта

```
drf-proj/
├── config/              # Настройки проекта
├── courses/             # Приложение с курсами и уроками
├── manage.py
├── .env.example         # Пример конфигурации окружения
├── .gitignore
├── README.md
└── pyproject.toml
```

## 👤 Автор

[Haohanmaiyami](https://github.com/Haohanmaiyami)

admin@mail.ru password admin - super user

"email": "newuser@mail.com",
  "password": "Strongpass123",
  "first_name": "Тест",
  "last_name": "Юзер",
  "phone": "1234567890"

#  Домашняя работа по сериализаторам

## Что было реализовано

- **Поле `lessons_count` в CourseSerializer**  
  Добавлено через `SerializerMethodField`, возвращает количество уроков, связанных с курсом.

- **Вложенный вывод уроков (`lessons`) в CourseSerializer**  
  Используется `LessonSerializer` для отображения всех уроков курса в одном ответе вместе с `lessons_count`.

- **Модель `Payment` в приложении `users`**  
  Поля: пользователь, дата оплаты, оплаченный курс или урок, сумма, метод оплаты (`cash` / `transfer`).  
  Реализованы связи с соответствующими моделями.

- **Тестовые данные для платежей**  
  Добавлены фикстуры `users/fixtures/payments.json` с примерами оплат курсов и уроков.

- **Фильтрация и сортировка для `/api/payments/`**  
  Поддержка фильтров по курсу, уроку, способу оплаты и сортировки по дате оплаты (возрастание/убывание).



# Домашняя работа: Права доступа в DRF

- JWT и закрытие API
Подключён JWT; по умолчанию все эндпоинты закрыты (IsAuthenticated). Открыты только: POST /api/register/, POST /api/token/, POST /api/token/refresh/. Профиль — через защищённые эндпоинты.

- Роли и пермишены модераторов
Фикстура группы moderators (users/fixtures/groups.json). Пермишены: IsModer, NotModer, IsOwner. В ViewSet права разведены по action: модератор читает/редактирует любые, но не создаёт и не удаляет.

- Владение объектами (курсы и уроки)
В моделях Course и Lesson добавлен owner (FK на пользователя). В perform_create() — автопривязка owner=self.request.user. В get_queryset() — фильтр «только свои» для немодераторов; объектный доступ через IsOwner.

# Домашняя работа: Валидаторы, пагинация, тесты

**Валидация**

* Задание 1: реализован валидатор ссылок (только youtube.com / youtu.be)
courses/validators.py → validate_youtube_url + подключён к LessonSerializer.video
Некорректные домены → 400 c ошибкой для поля video.

Задание 2: подписки на курс
Subscription(user, course, unique); toggle-эндпоинт POST /api/courses/subscribe/ (добавляет/удаляет подписку);
в CourseSerializer — флаг is_subscribed для текущего пользователя.

**Пагинация**

* Задание 3: courses/paginators.py → DefaultPagination(PageNumberPagination)
Параметры: page_size, page_size_query_param="page_size", max_page_size;
подключено в CourseViewSet и LessonViewSet.
Пример: GET /api/courses/?page=1&page_size=3

**Тесты**

* Задание 4: автотесты на CRUD уроков, валидатор (не-YouTube → 400), подписку (toggle + is_subscribed), пагинацию.



superuser:
admin2@mail.ru
admin

обычный пользователь
{"email":"user1@example.com","password":"Passw0rd!"}

модератор
{"email":"user_regular@example.com","password":"Passw0rd!"}

# Домашняя работа: Документация и безопасноть

## Реализовано

- Подключена и настроена документация **drf-yasg** (Swagger, ReDoc).  
- Реализована интеграция со **Stripe API**:  
  - создание продукта;  
  - создание цены;  
  - создание checkout-сессии;  
  - сохранение ссылки на оплату в модели `Payment`.  

Оплата протестирована на тестовых картах Stripe, редирект и сохранение данных работают корректно.


# Домашняя работа: Celery beat + Celery beat + Redis

## Что сделано:

Задание 1: настроен Celery (worker) и celery-beat (периодические задачи); Redis вынесен в .env.

Задание 2: при PATCH/PUT курса шлётся асинхронная рассылка подписчикам (Celery-task).

Задание 3: добавлена периодическая задача деактивации неактивных пользователей (через beat, по cron).

## Что использовалось:

- Django / DRF

- Celery + celery-beat

- Redis (broker / results)

- SMTP (Yandex Mail) для отправки писем

- .env для конфигурации (в т.ч. REDIS_URL, EMAIL_*)

- Postman — для проверки PATCH обновления курса

## ДЗ по DOCKER и DOCKER COMPOSE

SUPERUSER:
kharitonovayan2018@gmail.com
admin

Инструкция для запуска

## Запуск

Как запускать проект одной командой:

docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose ps - будет 5 сервисов celery, celery-beat, db, redis, web
docker compose exec web python manage.py createsuperuser

Как открыть бэкенд:

http://localhost:8000/swagger/

http://localhost:8000/redoc/

http://localhost:8000/admin/

http://localhost:8000/
