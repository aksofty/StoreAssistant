# StoreAssistant

FastAPI-приложение с AI-ассистентом для интернет-магазинов на базе GigaChat. Поддерживает запуск нескольких независимых копий на одном сервере через Traefik с автоматическим SSL.

---

## Содержание

- [Требования](#требования)
- [Структура проекта](#структура-проекта)
- [Локальный запуск (без Docker)](#локальный-запуск-без-docker)
- [Запуск в Docker](#запуск-в-docker)
  - [1. Запуск Traefik (один раз)](#1-запуск-traefik-один-раз)
  - [2. Запуск копии приложения](#2-запуск-копии-приложения)
  - [3. Запуск нескольких копий](#3-запуск-нескольких-копий)
- [Переменные окружения](#переменные-окружения)
- [Обновление с GitHub](#обновление-с-github)
- [Переменные окружения](#переменные-окружения)
- [Управление контейнерами](#управление-контейнерами)
- [Администрирование](#администрирование)
- [Подготовка чистого VPS](#подготовка-чистого-vps)

---

## Требования

- Python 3.11+
- Docker + Docker Compose (для продакшн-запуска)
- Домен с A-записью, указывающей на сервер (для SSL)
- Порты 80 и 443 должны быть открыты на сервере

---

## Структура проекта

```
StoreAssistant/
├── app/                    # Основной модуль приложения
├── static/                 # CSS/JS виджета
├── templates/              # Шаблоны admin-панели
├── main.py                 # Точка входа FastAPI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml      # Compose для одной копии приложения
├── .env                    # Настройки конкретного клиента
└── traefik/
    ├── docker-compose.yml  # Traefik (запускается один раз)
    ├── traefik.yml         # Конфигурация Traefik
    └── acme/               # SSL-сертификаты (создаётся автоматически)
```

Данные и логи каждого клиента хранятся в:
```
volumes/
├── data/{CLIENT_ID}/       # БД SQLite, FAISS-индексы, кэш
└── logs/{CLIENT_ID}/       # Файлы логов
```

---

## Локальный запуск (без Docker)

```bash
# 1. Создать и активировать виртуальное окружение
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить .env (скопировать и заполнить)
cp .env.example .env            # если есть шаблон
# Заполнить CLIENT_ID, GIGACHAT_CREDENTIALS и остальные поля

# 4. Запустить через python (порт берётся из FAST_API_PORT в .env)
python main.py

# Или напрямую через uvicorn на нужном порту
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Приложение будет доступно по адресу: `http://localhost:8000`

---

## Запуск в Docker

### 1. Запуск Traefik (один раз)

Traefik — обратный прокси, который принимает все входящие запросы на 80/443 и маршрутизирует их к нужным контейнерам с автоматическим SSL.

**Настройка перед первым запуском:**

Открыть [traefik/traefik.yml](traefik/traefik.yml) и указать реальный email для уведомлений Let's Encrypt:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: your@email.com   # ← заменить
```

**Запуск:**

```bash
cd traefik
docker compose up -d
```

Traefik создаёт Docker-сеть `traefik-public`, к которой подключаются все копии приложения. Сертификаты хранятся в `traefik/acme/acme.json` и автоматически обновляются.

Проверить статус:
```bash
docker compose logs -f traefik
```

---

### 2. Запуск копии приложения

Каждая копия приложения — это отдельная директория с собственным `.env`.

**Пример для клиента `example`:**

```bash
# Перейти в директорию проекта
cd /path/to/StoreAssistant

# Настроить .env
nano .env
```

Минимальный набор переменных в `.env`:

```env
REPO_DIR=/opt/StoreAssistant
CLIENT_ID=example
PORT=8000
DOMAIN=assistant.example.ru

GIGACHAT_CREDENTIALS=<base64-строка из личного кабинета>

FAST_API_SECRET_KEYS=["ваш_секретный_ключ"]
ALLOWED_ORIGINS=["https://example.ru"]

ADMIN_USERNAME=admin
ADMIN_PASSWORD=надёжный_пароль
ADMIN_SECRET_KEY=случайная_строка
```

**Собрать и запустить:**

```bash
docker compose up -d --build
```

Приложение будет доступно по адресу: `https://assistant.example.ru`

---

### 3. Запуск нескольких копий

Код приложения хранится в одном месте — клиенты отличаются только файлом `.env` и своими данными в `volumes/`.

**Рекомендуемая структура на сервере:**

```
/opt/
├── StoreAssistant/             ← git clone (код, один экземпляр)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── update.sh
│   └── ...
├── clients/
│   ├── example/
│   │   ├── .env                # CLIENT_ID=example, PORT=8080
│   │   └── volumes/
│   └── example2/
│       ├── .env                # CLIENT_ID=example2, PORT=8081
│       └── volumes/
└── traefik/                    # Общий Traefik (один экземпляр)
```

В `docker-compose.yml` каждого клиента путь к сборке указывает на общий код:

```yaml
services:
  app:
    build: /opt/StoreAssistant   # ← путь к репозиторию, не к .
    ...
```

**`.env` для каждого клиента:**

```env
# /opt/clients/example/.env
CLIENT_ID=example
PORT=8080
DOMAIN=assistant.example.ru
...

# /opt/clients/example2/.env
CLIENT_ID=example2
PORT=8081
DOMAIN=assistant.example2.ru
...
```

**Запуск конкретного клиента:**

```bash
REPO_DIR=/opt/StoreAssistant docker compose \
  -f /opt/StoreAssistant/docker-compose.yml \
  --env-file /opt/clients/example/.env \
  --project-directory /opt/clients/example \
  up -d --build
```

> `REPO_DIR` указывает Docker, где находится `Dockerfile`. Нужно передавать явно, потому что `--project-directory` меняет базовый путь для сборки на директорию клиента.

Traefik автоматически обнаружит новый контейнер и выпустит SSL-сертификат для домена из `DOMAIN`.

> **Важно:** каждый `CLIENT_ID` должен быть уникальным на сервере — он используется как имя контейнера и как имя роутера в Traefik.

> **Важно:** каждый `PORT` должен быть уникальным на сервере — он используется uvicorn внутри контейнера.

---

## Обновление с GitHub

Один `git pull` обновляет код для всех клиентов. Скрипт [update.sh](update.sh) пересобирает образы и перезапускает контейнеры.

```bash
# Обновить всех клиентов
bash /opt/StoreAssistant/update.sh

# Обновить конкретного клиента
bash /opt/StoreAssistant/update.sh example
```

Что делает скрипт:
1. `git pull` в директории с кодом
2. Для каждой директории в `/opt/clients/` запускает `docker compose up -d --build`
3. Данные клиентов в `volumes/` не затрагиваются

По умолчанию скрипт ищет клиентов в `/opt/clients/`. Путь можно переопределить переменной окружения:

```bash
CLIENTS_DIR=/srv/clients bash /opt/StoreAssistant/update.sh
```

---

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `CLIENT_ID` | Уникальный идентификатор клиента | `example` |
| `PORT` | Порт uvicorn внутри контейнера | `8000` |
| `DOMAIN` | Домен для SSL и маршрутизации | `assistant.example.ru` |
| `GIGACHAT_CREDENTIALS` | Base64-токен из личного кабинета GigaChat | `Njc0Zj...` |
| `GIGACHAT_CLIENT_ID` | Client ID из личного кабинета GigaChat | `674f9110-...` |
| `GIGACHAT_CLIENT_SECRET` | Client Secret из личного кабинета GigaChat | `f00f9cb1-...` |
| `ALLOWED_ORIGINS` | JSON-массив разрешённых CORS-доменов | `["https://example.ru"]` |
| `FAST_API_SECRET_KEYS` | JSON-массив ключей для авторизации запросов | `["key1", "key2"]` |
| `FAST_API_PORT` | Порт для локального запуска через `python main.py` | `8000` |
| `ADMIN_USERNAME` | Логин для admin-панели | `admin` |
| `ADMIN_PASSWORD` | Пароль для admin-панели | `секретный_пароль` |
| `ADMIN_SECRET_KEY` | Секрет сессий admin-панели | `случайная_строка` |

---

## Управление контейнерами

```bash
# Посмотреть статус
docker compose ps

# Логи в реальном времени
docker compose logs -f

# Перезапустить после изменения .env (без пересборки)
docker compose up -d

# Пересобрать образ и перезапустить (после изменений кода)
docker compose up -d --build

# Остановить
docker compose down

# Остановить и удалить volumes (осторожно — удалит данные!)
docker compose down -v
```

---

## Администрирование

Admin-панель доступна по адресу: `https://<DOMAIN>/admin`

Логин и пароль задаются в `.env` через `ADMIN_USERNAME` и `ADMIN_PASSWORD`.

Через панель можно:
- Управлять источниками данных (YML-каталог товаров, FAQ)
- Настраивать параметры ассистента (модель, промпт, температура)
- Просматривать историю сообщений пользователей
- Запускать синхронизацию данных вручную

---

## Подготовка чистого VPS

Инструкция для Ubuntu 22.04 / 24.04. На других Debian-based дистрибутивах команды аналогичны.

### 1. Первичная настройка системы

```bash
# Обновить пакеты
apt update && apt upgrade -y

# Установить базовые утилиты
apt install -y curl git ufw
```

### 2. Настройка фаервола

Открыть только необходимые порты: SSH, HTTP (для ACME-challenge Let's Encrypt), HTTPS.

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Проверить статус
ufw status
```

> **Важно:** убедитесь что правило `OpenSSH` добавлено **до** `ufw enable`, иначе потеряете доступ к серверу.

### 3. Установка Docker

```bash
# Добавить официальный репозиторий Docker
curl -fsSL https://get.docker.com | bash

# Запустить Docker и добавить в автозапуск
systemctl enable --now docker

# Проверить установку
docker --version
docker compose version
```

### 4. Проверка DNS

Перед запуском Traefik убедитесь, что A-запись домена указывает на IP сервера:

```bash
# Проверить резолвинг домена (заменить на свой)
dig +short assistant.example.ru
# Должен вернуть IP вашего сервера
```

Let's Encrypt не выдаст сертификат, если домен не резолвится в IP сервера.

### 5. Структура директорий

```bash
mkdir -p /opt/StoreAssistant
mkdir -p /opt/clients
mkdir -p /opt/traefik
```

### 6. Клонирование репозитория

```bash
git clone https://github.com/aksofty/StoreAssistant.git /opt/StoreAssistant
```

### 7. Настройка Traefik

```bash
# Скопировать конфиг Traefik
cp -r /opt/StoreAssistant/traefik/* /opt/traefik/

# Указать email в конфиге (обязательно!)
nano /opt/traefik/traefik.yml

# Запустить Traefik
cd /opt/traefik
docker compose up -d

# Убедиться что запустился
docker compose logs traefik
```

### 8. Добавление первого клиента

```bash
# Создать директорию клиента
mkdir -p /opt/clients/example/volumes

# Создать .env
nano /opt/clients/example/.env
```

Заполнить `.env`:

```env
REPO_DIR=/opt/StoreAssistant
CLIENT_ID=example
PORT=8000
DOMAIN=assistant.example.ru

GIGACHAT_CREDENTIALS=<токен>
FAST_API_SECRET_KEYS=["секретный_ключ"]
ALLOWED_ORIGINS=["https://example.ru"]

ADMIN_USERNAME=admin
ADMIN_PASSWORD=надёжный_пароль
ADMIN_SECRET_KEY=случайная_строка_32_символа
```

Запустить:

```bash
REPO_DIR=/opt/StoreAssistant docker compose \
  -f /opt/StoreAssistant/docker-compose.yml \
  --env-file /opt/clients/example/.env \
  --project-directory /opt/clients/example \
  up -d --build
```

### 9. Проверка

```bash
# Все контейнеры запущены
docker ps

# Traefik получил сертификат (подождать ~30 секунд после первого запуска)
docker logs traefik 2>&1 | grep -i "acme\|certificate\|error"

# Приложение отвечает
curl -I https://assistant.myclient.ru
```
