# 📚 DRF Project

Учебный проект на **Django REST Framework** для платформы онлайн-обучения (LMS).

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

"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc1NDY0OTgwNywiaWF0IjoxNzU0NTYzNDA3LCJqdGkiOiIwZTZmZjdiMDJkNDE0OTJkODJkZjlmYjlkMTg4OWZhMSIsInVzZXJfaWQiOiIyIn0.9s5YLIAtYpxqYVtm1UGifXt6ylyaCnn28P1bsTex-lU",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU0NTYzNzA3LCJpYXQiOjE3NTQ1NjM0MDcsImp0aSI6IjJhNDcxYjg2YTk1YTQ5YzI5OTE4NDQ4YmVmZjA2YTM1IiwidXNlcl9pZCI6IjIifQ.fua9xOi5FdsZgvg462Zgd4TDOQDM-UwpbkiDBA1vTIA"