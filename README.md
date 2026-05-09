# Двухсервисная система LLM-консультаций


---

## Архитектура

```text
Пользователь
→ Auth Service
→ JWT
→ Telegram Bot
→ проверка JWT
→ Redis
→ RabbitMQ
→ Celery Worker
→ OpenRouter
→ Telegram
```

Архитектура построена по принципу разделения ответственности.

`Auth Service` является отдельным FastAPI-сервисом. Он создаёт пользователей, проверяет пароль при логине и выдаёт JWT. Именно этот сервис является единственным местом, где создаётся токен.

`Bot Service` является отдельным сервисом Telegram-бота. Он принимает JWT от пользователя через команду `/token <jwt>`, проверяет подпись и срок действия токена. Если токен корректный, бот сохраняет его в Redis и разрешает пользователю отправлять вопросы к LLM.

Запросы к LLM не выполняются напрямую в Telegram-хэндлере. Бот отправляет задачу в RabbitMQ, а Celery Worker забирает её из очереди, обращается к OpenRouter и отправляет пользователю ответ в Telegram.

---

## Назначение сервисов

### Auth Service

`auth_service` отвечает за регистрацию, вход пользователя и выпуск JWT.

Реализованные эндпоинты:

```text
POST /auth/register
POST /auth/login
GET  /auth/me
GET  /health
```

Назначение эндпоинтов:

```text
POST /auth/register — регистрация пользователя
POST /auth/login    — логин и получение JWT
GET  /auth/me       — получение профиля текущего пользователя по JWT
GET  /health        — проверка работоспособности сервиса
```

Пароль пользователя хранится только в виде хеша.  
JWT содержит поля:

```text
sub  — id пользователя
role — роль пользователя
iat  — время выпуска токена
exp  — время истечения токена
```

---

### Bot Service

`bot_service` отвечает за работу Telegram-бота и обработку LLM-запросов.

Бот выполняет следующие действия:

```text
принимает JWT от пользователя
проверяет JWT
сохраняет JWT в Redis по Telegram user_id
принимает текстовый вопрос
публикует задачу в RabbitMQ
получает результат обработки через Celery Worker
отправляет ответ пользователю в Telegram
```

Bot Service не создаёт JWT и не хранит пользователей.  
Он только проверяет токен, который был выдан Auth Service.

---

## Redis, RabbitMQ и Celery

В проекте используются Redis, RabbitMQ и Celery.

```text
Redis    — хранит JWT, привязанный к Telegram user_id
RabbitMQ — используется как брокер задач
Celery   — выполняет фоновые LLM-запросы
```

Это нужно для того, чтобы Telegram-бот не зависал во время ожидания ответа от LLM.  
Когда пользователь отправляет вопрос, бот быстро отвечает:

```text
Запрос принят. Ответ придёт через несколько секунд.
```

После этого Celery Worker обрабатывает задачу в фоне и отправляет итоговый ответ пользователю.

---

## Сценарий работы

```text
1. Пользователь открывает Swagger Auth Service.
2. Пользователь регистрируется через POST /auth/register.
3. Пользователь выполняет логин через POST /auth/login.
4. Auth Service возвращает JWT.
5. Пользователь открывает Telegram-бота.
6. Пользователь отправляет JWT командой /token <jwt>.
7. Bot Service проверяет токен.
8. Bot Service сохраняет токен в Redis.
9. Пользователь отправляет вопрос боту.
10. Bot Service публикует задачу в RabbitMQ.
11. Celery Worker забирает задачу из очереди.
12. Celery Worker отправляет запрос в OpenRouter.
13. OpenRouter возвращает ответ LLM.
14. Celery Worker отправляет ответ пользователю в Telegram.
```

---

## Запуск проекта

### 1. Запуск Redis и RabbitMQ

Из корня проекта:

```bash
docker compose up -d
```

Проверка:

```bash
docker compose ps
```

RabbitMQ UI:

```text
http://localhost:15672
```

Логин и пароль:

```text
guest / guest
```

---

### 2. Запуск Auth Service

```bash
cd auth_service
uv venv
.venv\Scripts\Activate.ps1
uv pip install -e .
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger Auth Service:

```text
http://127.0.0.1:8000/docs
```

---

### 3. Запуск Bot Service

```bash
cd bot_service
uv venv
.venv\Scripts\Activate.ps1
uv pip install -e .
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Swagger Bot Service:

```text
http://127.0.0.1:8001/docs
```

---

### 4. Запуск Celery Worker

```bash
cd bot_service
.venv\Scripts\Activate.ps1
uv run celery -A app.infra.celery_app:celery_app worker --loglevel=info --pool=solo
```

На Windows используется параметр:

```text
--pool=solo
```

---

### 5. Запуск Telegram-бота

```bash
cd bot_service
.venv\Scripts\Activate.ps1
uv run python -m app.bot.dispatcher
```

---

## Переменные окружения

### auth_service/.env.example

```env
APP_NAME=auth-service
ENV=local

JWT_SECRET=change_me_super_secret
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

SQLITE_PATH=./auth.db
```

### bot_service/.env.example

```env
APP_NAME=bot-service
ENV=local

TELEGRAM_BOT_TOKEN=

JWT_SECRET=change_me_super_secret
JWT_ALG=HS256

REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672//

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openrouter/free
OPENROUTER_SITE_URL=https://example.com
OPENROUTER_APP_NAME=bot-service
```

Файлы `.env` не добавляются в репозиторий, так как содержат секретные токены.

---

## Тестирование

### Auth Service

```bash
cd auth_service
uv run pytest
```

Результат:

```text
6 passed
```

### Bot Service

```bash
cd bot_service
uv run pytest
```

Результат:

```text
6 passed
```

Тесты проверяют:

```text
хеширование и проверку паролей
создание и декодирование JWT
регистрацию пользователя
логин пользователя
доступ к /auth/me по JWT
ошибки авторизации
проверку JWT в Bot Service
сохранение JWT в Redis
вызов Celery-задачи
мок-запрос к OpenRouter
```

---

## Скриншоты работы

### Регистрация пользователя в Auth Service

![alt text](<screenshots/Снимок экрана 2026-05-09 015307.png>)

### Логин и получение JWT

![alt text](<screenshots/Снимок экрана 2026-05-09 015355.png>)

### Получение профиля через /auth/me

![alt text](<screenshots/Снимок экрана 2026-05-09 015510.png>)

### Передача JWT Telegram-боту
![alt text](<screenshots/Снимок экрана 2026-05-09 020446.png>)

### Ответ LLM в Telegram

![alt text](<screenshots/Снимок экрана 2026-05-09 020609.png>)

### RabbitMQ Overview

![alt text](<screenshots/Снимок экрана 2026-05-09 020908.png>)

### RabbitMQ Queues

![alt text](<screenshots/Снимок экрана 2026-05-09 021036.png>)

### Успешные тесты Auth Service

![alt text](<screenshots/Снимок экрана 2026-05-09 021109.png>)

### Успешные тесты Bot Service

![alt text](<screenshots/Снимок экрана 2026-05-09 021229.png>)

### Запущенные Redis и RabbitMQ

![alt text](<screenshots/Снимок экрана 2026-05-09 021322.png>)

