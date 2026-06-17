foodgram_domain: https://ilyahost.sytes.net
# Foodgram — Продуктовый помощник

Foodgram — это онлайн-платформа и социальная сеть для любителей готовить. Сервис позволяет пользователям публиковать собственные рецепты, подписываться на публикации других авторов, добавлять понравившиеся блюда в список «Избранное», а перед походом в магазин скачивать сводный список покупок со всеми необходимыми ингредиентами.

## Стек технологий
* **Backend:** Python, Django, Django REST Framework, Djoser, Django Filters
* **Database:** PostgreSQL (Production) / SQLite (Development)
* **Containerization:** Docker, Docker Compose
* **Web Server & Reverse Proxy:** Nginx
* **CI/CD:** GitHub Actions

## Как развернуть проект в Docker (Локально)

1. Клонируйте репозиторий на локальную машину:
```bash
git clone git@github.com:твой_логин_на_github/foodgram-project-react.git
cd foodgram-project-react
```

2. Перейдите в папку с конфигурационными файлами контейнеров:
```bash
cd infra
```

3. Создайте файл `.env` внутри папки `infra/` со следующими переменными окружения:
```env
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_HOST=db
DB_PORT=5432
SECRET_KEY=django-secret-key
DEBUG=True(False по умолчанию)
ALLOWED_HOSTS=(ваш домен)
CSRF_TRUSTED_ORIGINS=(ваш домен)
```

4. Запустите сборку и развёртывание контейнеров:
```bash
docker compose up -d --build
```

5. Выполните миграции внутри контейнера бэкенда:
```bash
docker compose exec backend python manage.py migrate
```

6. Соберите статические файлы приложения:
```bash
docker compose exec backend python manage.py collectstatic --no-input
```

7. Создайте суперпользователя (администратора):
```bash
docker compose exec backend python manage.py createsuperuser
```

Проект станет доступен по адресу: http://localhost:8000/

## Как наполнить базу данных ингредиентами

В проекте предусмотрена автоматическая загрузка подготовленного списка ингредиентов из CSV-файла. Для наполнения базы данных выполните команду:

```bash
docker compose exec backend python manage.py load_ingredients
```

## Документация API

Полная спецификация API (документация Swagger/Redoc) доступна после запуска контейнеров по адресам:
* Redoc: http://localhost:8000/api/docs/redoc.html
* Swagger UI: http://localhost:8000/api/docs/

### Примеры запросов и ответов

#### 1. Получение списка ингредиентов
* **Запрос:** `GET /api/ingredients/?name=ветчина`
* **Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Ветчина",
    "measurement_unit": "г"
  }
]
```

#### 2. Регистрация нового пользователя
* **Запрос:** `POST /api/users/`
* **Тело запроса:**
```json
{
  "email": "user@example.com",
  "username": "chef_master",
  "first_name": "Иван",
  "last_name": "Иванов",
  "password": "secure_password123"
}
```
* **Ответ (201 Created):**
```json
{
  "email": "user@example.com",
  "id": 5,
  "username": "chef_master",
  "first_name": "Иван",
  "last_name": "Иванов"
}
```

#### 3. Получение короткой ссылки на рецепт
* **Запрос:** `GET /api/recipes/1/get-link/` (Доступно авторизованным пользователям)
* **Ответ (200 OK):**
```json
{
  "short-link": "http://localhost:8000/s/aB3xD9"
}
```

## Автор проекта
Разработчик: [Ваше Имя / Никнейм на GitHub](https://github.com)
