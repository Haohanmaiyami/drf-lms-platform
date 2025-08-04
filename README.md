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
