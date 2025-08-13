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



# Домашняя работа: Права доступа в DRF

- JWT и закрытие API
Подключён JWT; по умолчанию все эндпоинты закрыты (IsAuthenticated). Открыты только: POST /api/register/, POST /api/token/, POST /api/token/refresh/. Профиль — через защищённые эндпоинты.

- Роли и пермишены модераторов
Фикстура группы moderators (users/fixtures/groups.json). Пермишены: IsModer, NotModer, IsOwner. В ViewSet права разведены по action: модератор читает/редактирует любые, но не создаёт и не удаляет.

- Владение объектами (курсы и уроки)
В моделях Course и Lesson добавлен owner (FK на пользователя). В perform_create() — автопривязка owner=self.request.user. В get_queryset() — фильтр «только свои» для немодераторов; объектный доступ через IsOwner.


superuser:
admin2@mail.ru
admin

обычный пользователь
{"email":"user1@example.com","password":"Passw0rd!"}

модератор
{"email":"user_regular@example.com","password":"Passw0rd!"}

