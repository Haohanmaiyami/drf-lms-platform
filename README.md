# 📚 DRF LMS Platform

Учебный backend-проект платформы онлайн-обучения (LMS), реализованный на **Django REST Framework** с поддержкой Docker, Celery и платежей.

---

## 🚀 Быстрый запуск (Docker)

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Haohanmaiyami/drf-proj.git
cd drf-proj
```

---

### 2. Создать `.env`

Создай файл `.env` на основе `.env.example`

Пример:

```env
SECRET_KEY=your-secret-key
DEBUG=True

POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
```

---

### 3. Запуск проекта

```bash
docker compose up --build
```

---

### 4. Открыть в браузере

* 🔹 Swagger → http://localhost:8000/swagger/
* 🔹 ReDoc → http://localhost:8000/redoc/
* 🔹 Admin → http://localhost:8000/admin/
* 🔹 API → http://localhost:8000/

---

## 🔐 Тестовые пользователи

### 👑 Superuser

```
email: kharitonovayan2018@gmail.com
password: admin
```

### 👤 Обычный пользователь

```
email: user1@example.com
password: Passw0rd!
```

### 🛡️ Модератор

```
email: user_regular@example.com
password: Passw0rd!
```

---

## 🧪 Основные эндпоинты

```
POST   /api/register/
POST   /api/token/
POST   /api/token/refresh/

GET    /api/courses/
POST   /api/courses/

GET    /api/lessons/
POST   /api/lessons/

POST   /api/courses/subscribe/

GET    /api/payments/
```

---

## ⚙️ Стек технологий

* 🐍 Python 3.12 (Docker)
* 🌐 Django
* 🔗 Django REST Framework
* 🐘 PostgreSQL
* ⚡ Redis
* 🔄 Celery + Celery Beat
* 🐳 Docker / Docker Compose
* 💳 Stripe API

---

## 📦 Основной функционал

### 📚 Курсы и уроки

* CRUD для курсов и уроков
* Вложенные уроки внутри курса
* Подсчёт количества уроков

---

### 🔐 Аутентификация

* JWT (access / refresh токены)
* Закрытый API (IsAuthenticated)

---

### 👥 Роли и права доступа

* пользователь

* модератор

* администратор

* модератор может:

  * читать и редактировать любые данные

* пользователь:

  * работает только со своими объектами

---

### 💳 Платежи

* интеграция со Stripe
* создание checkout session
* сохранение ссылок на оплату

---

### 📩 Рассылки

* асинхронные задачи через Celery
* уведомления при обновлении курса

---

### ⏱️ Периодические задачи

* Celery Beat
* деактивация неактивных пользователей

---

### ✅ Валидация

* проверка ссылок только на YouTube
* защита данных на уровне сериализаторов

---

### 📄 Пагинация

* PageNumberPagination
* настройка размера страницы

---

### 🧪 Тестирование

* CRUD тесты
* подписки
* валидаторы
* пагинация

---

## 🧠 Архитектура

Проект разделён на приложения:

```
config/      # настройки Django
courses/     # курсы, уроки, подписки
users/       # пользователи и платежи
```

---

## 🐳 Docker архитектура

Проект запускается через docker-compose и включает:

* web (Django)
* db (PostgreSQL)
* redis
* celery (worker)
* celery-beat

---

## 👨‍💻 Автор

👉 https://github.com/Haohanmaiyami

---

## 💬 Примечание

Проект полностью готов для локального запуска через Docker и может использоваться как backend для frontend-приложений (например, Flutter).

---
