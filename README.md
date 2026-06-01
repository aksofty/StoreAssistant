# StoreAssistant

FastAPI-приложение с AI-ассистентом для интернет-магазинов на базе GigaChat. Запускается в Docker с Traefik в качестве обратного прокси и автоматическим SSL от Let's Encrypt.

---

## Содержание

- [Требования](#требования)
- [Структура проекта](#структура-проекта)
- [Локальный запуск (без Docker)](#локальный-запуск-без-docker)
- [Запуск в Docker](#запуск-в-docker)
  - [1. Запуск Traefik](#1-запуск-traefik-один-раз)
  - [2. Запуск приложения](#2-запуск-приложения)
- [Переменные окружения](#переменные-окружения)
- [Обновление с GitHub](#обновление-с-github)
- [Управление контейнерами](#управление-контейнерами)
- [Администрирование](#администрирование)
- [Подготовка чистого VPS](#подготовка-чистого-vps)

---

## Требования

- Python 3.11+
- Docker + Docker Compose (для продакшн-запуска)
- Домен с A-записью, указывающей на сервер (для SSL)
- Порты 80 и 443 открыты на сервере

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
├── docker-compose.yml
├── update.sh               # Скрипт обновления с GitHub
├── .env                    # Настройки приложения
└── traefik/
    ├── docker-compose.yml  # Traefik (запускается один раз)
    ├── traefik.yml         # Конфигурация Traefik
    └── acme/               # SSL-сертификаты (создаётся автоматически)
```

Данные и логи хранятся в:
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

# 3. Настроить .env
cp .env.example .env
# Заполнить CLIENT_ID, GIGACHAT_CREDENTIALS и остальные поля

# 4. Запустить
python main.py

# Или напрямую через uvicorn
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

Traefik создаёт Docker-сеть `traefik-public`, к которой подключается приложение. Сертификаты хранятся в `traefik/acme/acme.json` и автоматически обновляются.

Проверить статус:
```bash
docker compose logs -f traefik
```

---

### 2. Запуск приложения

**Настроить `.env`:**

```env
CLIENT_ID=mystore
PORT=8080
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
cd /opt/StoreAssistant
docker compose up -d --build
```

Приложение будет доступно по адресу: `https://assistant.example.ru`

Traefik автоматически обнаружит контейнер через Docker labels и выпустит SSL-сертификат для домена из `DOMAIN`.

---

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `CLIENT_ID` | Идентификатор для папок с данными и логами | `mystore` |
| `PORT` | Порт uvicorn внутри контейнера | `8080` |
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

## Обновление с GitHub

```bash
bash /opt/StoreAssistant/update.sh
```

Скрипт выполняет `git pull` и пересобирает/перезапускает контейнер. Данные в `volumes/` не затрагиваются.

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

Инструкция для Ubuntu 22.04 / 24.04.

### 1. Первичная настройка системы

```bash
apt update && apt upgrade -y
apt install -y curl git ufw
```

### 2. Настройка фаервола

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

ufw status
```

> **Важно:** правило `OpenSSH` добавлять **до** `ufw enable`, иначе потеряете доступ к серверу.

### 3. Установка Docker

```bash
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker

docker --version
docker compose version
```

### 4. Проверка DNS

Перед запуском Traefik убедитесь, что A-запись домена указывает на IP сервера:

```bash
dig +short assistant.example.ru
# Должен вернуть IP вашего сервера
```

Let's Encrypt не выдаст сертификат, если домен не резолвится корректно.

### 5. Клонирование репозитория

```bash
git clone https://github.com/aksofty/StoreAssistant.git /opt/StoreAssistant
```

### 6. Настройка и запуск Traefik

```bash
# Указать email в конфиге (обязательно!)
nano /opt/StoreAssistant/traefik/traefik.yml

# Запустить Traefik
cd /opt/StoreAssistant/traefik
docker compose up -d

# Убедиться что запустился без ошибок
docker compose logs traefik
```

### 7. Настройка и запуск приложения

```bash
cd /opt/StoreAssistant

# Заполнить .env
nano .env

# Собрать и запустить
docker compose up -d --build
```

### 8. Проверка

```bash
# Все контейнеры запущены
docker ps

# Traefik получил сертификат (подождать ~30 секунд после первого запуска)
docker logs traefik 2>&1 | grep -i "acme\|certificate\|error"

# Приложение отвечает
curl -I https://assistant.example.ru
```
