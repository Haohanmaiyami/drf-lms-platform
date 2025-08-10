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


{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc1NTY2NzkyMywiaWF0IjoxNzU1MDYzMTIzLCJqdGkiOiI1MDA0MDVkNWFjNzc0NjJjYTUzMjk2MTgxNmZhZDMyZCIsInVzZXJfaWQiOiIxIn0.MpoLrmDuTy8NMhf2hzHYLJWlHQ_jY6xDBH8A_Y4qiV8",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1MDY2NzIzLCJpYXQiOjE3NTUwNjMxMjMsImp0aSI6ImY5ZGY4NzhkNTZkMTQyZjhiNjUxZDNiMmRhMjgzMjg5IiwidXNlcl9pZCI6IjEifQ.-ixxyy--pH8BLmiQiyiDtkCfeaIFEjLETxjywoPSwgc"
}

{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc1NTY3MTEzMSwiaWF0IjoxNzU1MDY2MzMxLCJqdGkiOiIxMGQ5YWYwNTFhMjg0Y2I0YmQ5NjY5MjI1YzM4OGFjNCIsInVzZXJfaWQiOiIxIn0.WyAUNAm2H2HOzyiKxYLD2kJc5o0O6dTMksaJUyMNVX8",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1MDY5OTMxLCJpYXQiOjE3NTUwNjYzMzEsImp0aSI6IjMyZWI4OTQwY2I0ZTRiZDRhNGVhYjY0YjJhYWM1MmM1IiwidXNlcl9pZCI6IjEifQ.ls0zcrQ9ZqwD8dCju2ANyV8a5uoAcAD1MQbwdQwUkhQ"
}

COURSE_ES 1  испанский фонетика урок 1 грамматика урок 2
COURSE_ZH 2 фонетика тоны пиньинь 3

1990$ за весь курс испанский кэш 6 37 айди 1
750$ за урок испанский фонетика трансфер 6 40 айди 2 изменил на 2190 изменил на 1 доллар



