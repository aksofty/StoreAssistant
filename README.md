# StoreAssistant

FastAPI-приложение с AI-ассистентом для интернет-магазинов на базе GigaChat. Запускается в Docker с Traefik в качестве обратного прокси и автоматическим SSL от Let's Encrypt. Поддерживает запуск нескольких независимых экземпляров (клиентов) на одном сервере.

---

## Содержание

- [Требования](#требования)
- [Структура проекта](#структура-проекта)
- [Локальный запуск (без Docker)](#локальный-запуск-без-docker)
- [Запуск в Docker](#запуск-в-docker)
  - [1. Запуск Traefik](#1-запуск-traefik-один-раз)
  - [2. Настройка клиента](#2-настройка-клиента)
  - [3. Запуск клиента](#3-запуск-клиента)
- [Обновление](#обновление)
- [Управление контейнерами](#управление-контейнерами)
- [Переменные окружения](#переменные-окружения)
- [Администрирование](#администрирование)
- [Подготовка чистого VPS](#подготовка-чистого-vps)

---

## Требования

- Python 3.12+
- Docker + Docker Compose
- Домен с A-записью, указывающей на сервер
- Порты 80 и 443 открыты на сервере

---

## Структура проекта

```
PROJECTS/
├── StoreAssistant/             # Код приложения (один на всех клиентов)
│   ├── app/
│   ├── main.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── update.sh
│   └── traefik/
└── volumes/
    └── data/
        ├── client1/            # Данные клиента 1
        │   ├── .env            # Конфиг клиента 1
        │   ├── db/
        │   ├── cache/
        │   ├── faiss_index/
        │   ├── logs/
        │   └── tools/
        │       └── tools.py    # Кастомные инструменты клиента
        └── client2/            # Данные клиента 2
            └── .env
```

---

## Локальный запуск (без Docker)

```bash
# 1. Создать и активировать виртуальное окружение
python -m venv venv
source venv/bin/activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить .env
cp .env.example .env
# Заполнить CLIENT_ID, GIGACHAT_CREDENTIALS и остальные поля

# 4. Запустить
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Запуск в Docker

### 1. Запуск Traefik (один раз)

Указать email в конфиге:

```yaml
# traefik/traefik.yml
certificatesResolvers:
  letsencrypt:
    acme:
      email: your@email.com
```

Запустить:

```bash
cd traefik
docker compose up -d
```

### 2. Настройка клиента

Создать папку и `.env` для каждого клиента:

```bash
mkdir -p ../volumes/data/mystore
nano ../volumes/data/mystore/.env
```

Минимальный `.env`:

```env
CLIENT_ID=mystore
PORT=8080
DOMAIN=assistant.example.ru

GIGACHAT_CREDENTIALS=<base64-строка>
GIGACHAT_CLIENT_ID=<uuid>
GIGACHAT_CLIENT_SECRET=<uuid>

FAST_API_SECRET_KEYS=["секретный_ключ"]
ALLOWED_ORIGINS=["https://example.ru"]

ADMIN_USERNAME=admin
ADMIN_PASSWORD=надёжный_пароль
ADMIN_SECRET_KEY=случайная_строка
```

### 3. Запуск клиента

```bash
docker compose --env-file ../volumes/data/mystore/.env up -d --build
```

Для каждого дополнительного клиента — та же команда с другим `--env-file`.

---

## Обновление

Обновить одного клиента:

```bash
./update.sh mystore
```

Обновить всех клиентов сразу:

```bash
./update.sh --all
```

Скрипт выполняет `git pull` и пересобирает/перезапускает контейнер. Данные в `StoreAssistant_volumes/` не затрагиваются.

---

## Управление контейнерами

Все команды требуют `--env-file` для указания клиента:

```bash
# Статус контейнера
docker compose --env-file ../StoreAssistant_volumes/data/mystore/.env ps

# Логи в реальном времени
docker compose --env-file ../StoreAssistant_volumes/data/mystore/.env logs -f

# Перезапустить без пересборки
docker compose --env-file ../StoreAssistant_volumes/data/mystore/.env up -d

# Остановить
docker compose --env-file ../StoreAssistant_volumes/data/mystore/.env down
```

---

## Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `CLIENT_ID` | Идентификатор клиента (имя папки в `StoreAssistant_volumes/data/`) | `mystore` |
| `PORT` | Порт uvicorn внутри контейнера | `8080` |
| `DOMAIN` | Домен для SSL и маршрутизации | `assistant.example.ru` |
| `GIGACHAT_CREDENTIALS` | Base64-токен из личного кабинета GigaChat | `Njc0Zj...` |
| `GIGACHAT_CLIENT_ID` | Client ID из личного кабинета GigaChat | `674f9110-...` |
| `GIGACHAT_CLIENT_SECRET` | Client Secret из личного кабинета GigaChat | `f00f9cb1-...` |
| `ALLOWED_ORIGINS` | JSON-массив разрешённых CORS-доменов | `["https://example.ru"]` |
| `FAST_API_SECRET_KEYS` | JSON-массив ключей для авторизации запросов | `["key1", "key2"]` |
| `ADMIN_USERNAME` | Логин для admin-панели | `admin` |
| `ADMIN_PASSWORD` | Пароль для admin-панели | `секретный_пароль` |
| `ADMIN_SECRET_KEY` | Секрет сессий admin-панели | `случайная_строка` |

---

## Администрирование

Admin-панель доступна по адресу: `https://<DOMAIN>/admin`

Через панель можно:
- Управлять источниками данных (YML-каталог товаров, FAQ)
- Настраивать параметры ассистента (модель, промпт, температура)
- Просматривать историю сообщений пользователей
- Запускать синхронизацию данных вручную

---

## Кастомные инструменты

Каждый клиент может определять собственные инструменты для ассистента в файле `StoreAssistant_volumes/data/{CLIENT_ID}/tools/tools.py`:

```python
from langchain_core.tools import tool

@tool
def get_delivery_price(text: str) -> str:
    """Возвращает стоимость доставки."""
    return "Стоимость доставки 500 рублей"
```

Файл подхватывается автоматически при старте приложения.

---

## Подготовка чистого VPS

Инструкция для Ubuntu 22.04 / 24.04.

### 1. Первичная настройка

```bash
apt update && apt upgrade -y
apt install -y curl git ufw
```

### 2. Фаервол

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

> **Важно:** правило `OpenSSH` добавлять **до** `ufw enable`.

### 3. Docker

```bash
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker
```

### 4. Клонирование репозитория

```bash
git clone https://github.com/aksofty/StoreAssistant.git /opt/StoreAssistant
```

### 5. Запуск Traefik

```bash
nano /opt/StoreAssistant/traefik/traefik.yml  # указать email
cd /opt/StoreAssistant/traefik
docker compose up -d
```

### 6. Настройка и запуск первого клиента

```bash
mkdir -p /opt/StoreAssistant_volumes/data/mystore
nano /opt/StoreAssistant_volumes/data/mystore/.env

cd /opt/StoreAssistant
docker compose --env-file /opt/StoreAssistant_volumes/data/mystore/.env up -d --build
```

### 7. Проверка

```bash
docker ps
curl -I https://assistant.example.ru
```
