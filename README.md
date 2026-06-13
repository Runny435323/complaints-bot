# 🤖 Telegram-бот: аналитика жалоб

## Структура проекта

```
complaints_bot/
├── bot.py          — основной файл бота
├── queries.py      — все MongoDB-запросы
├── db_setup.py     — создание индексов + тестовые данные
├── schema.py       — описание схемы коллекции
└── requirements.txt
```

## Быстрый старт

### 1. Установить зависимости
```bash
pip install -r requirements.txt
```

### 2. Прописать настройки
В `bot.py` (или через переменные окружения):
```python
TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
MONGO_URI = "mongodb://localhost:27017"  # или ваш URI
```

Через env-переменные (рекомендуется):
```bash
export BOT_TOKEN="7123456789:AAFxxx..."
export MONGO_URI="mongodb://user:pass@host:27017"
```

### 3. Инициализировать БД
```bash
python db_setup.py
```
Создаст индексы и добавит 100 тестовых жалоб.

### 4. Запустить бота
```bash
python bot.py
```

---

## Схема документа в MongoDB

| Поле             | Тип        | Описание                              |
|------------------|------------|---------------------------------------|
| `complaint_number` | string   | Уникальный номер (CMP-2024-001)       |
| `title`          | string     | Краткое название                      |
| `description`    | string     | Полное описание                       |
| `department`     | string     | Отдел (IT, HR, Finance...)            |
| `status`         | string     | open / in_progress / closed           |
| `resolution`     | string     | approved / rejected / null            |
| `priority`       | string     | low / medium / high                   |
| `created_at`     | datetime   | Дата создания                         |
| `closed_at`      | datetime   | Дата закрытия (null если не закрыта)  |
| `assigned_to`    | string     | Ответственный сотрудник               |
| `created_by`     | string     | Кто подал жалобу                      |

---

## Доступные отчёты

| # | Отчёт | Что показывает |
|---|-------|----------------|
| 1 | 📦 Закрытые жалобы | Количество закрытых за период |
| 2 | ⏱ Время рассмотрения | Среднее/мин/макс, самая быстрая и долгая |
| 3 | 🏆 Рейтинг сотрудников | Кто больше всего закрыл |
| 4 | 🏢 По отделам | Сколько жалоб в каждом отделе |
| 5 | 📊 Статусы | Открыто/в работе/закрыто/одобрено/отказано |

---

## Как добавить жалобу из другого сервиса

```python
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

client = AsyncIOMotorClient("mongodb://localhost:27017")
col = client["complaints_db"]["complaints"]

await col.insert_one({
    "complaint_number": "CMP-2024-101",
    "title": "Не работает принтер",
    "description": "Принтер на 3-м этаже не печатает",
    "department": "IT",
    "status": "open",
    "resolution": None,
    "priority": "medium",
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    "closed_at": None,
    "assigned_to": "Иванов Иван",
    "created_by": "Петров Пётр",
})
```
