"""
Инициализация БД: создание индексов и тестовые данные
Запустить один раз: python db_setup.py
"""

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from datetime import datetime, timedelta
import random

MONGO_URI = "mongodb+srv://testacc:DB0Uzp4Myu8qLwod@cluster0.kuwhy7o.mongodb.net/?appName=Cluster0"
DB_NAME = "complaints_db"

DEPARTMENTS = ["IT", "HR", "Finance", "Operations", "Legal"]
EMPLOYEES = [
    "Иванов Иван", "Петрова Мария", "Сидоров Алексей",
    "Козлова Елена", "Новиков Дмитрий", "Морозова Анна"
]
STATUSES = ["open", "in_progress", "closed"]
RESOLUTIONS = ["approved", "rejected"]
PRIORITIES = ["low", "medium", "high"]


async def setup():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["complaints"]

    # Индексы
    await col.create_index("complaint_number", unique=True)
    await col.create_index([("status", 1), ("closed_at", 1)])
    await col.create_index("department")
    await col.create_index("assigned_to")
    await col.create_index("created_at")
    print("✅ Индексы созданы")

    # Тестовые данные (100 жалоб за последние 6 месяцев)
    docs = []
    for i in range(1, 101):
        created = datetime.now() - timedelta(days=random.randint(1, 180))
        status = random.choice(STATUSES)
        closed_at = None
        resolution = None
        if status == "closed":
            closed_at = created + timedelta(hours=random.randint(2, 240))
            resolution = random.choice(RESOLUTIONS)

        docs.append({
            "complaint_number": f"CMP-{created.year}-{i:03d}",
            "title": f"Жалоба №{i}",
            "description": f"Описание жалобы номер {i}",
            "department": random.choice(DEPARTMENTS),
            "status": status,
            "resolution": resolution,
            "priority": random.choice(PRIORITIES),
            "created_at": created,
            "updated_at": closed_at or created,
            "closed_at": closed_at,
            "assigned_to": random.choice(EMPLOYEES),
            "created_by": f"Пользователь {random.randint(1, 30)}",
        })

    await col.delete_many({})
    await col.insert_many(docs)
    print(f"✅ Добавлено {len(docs)} тестовых жалоб")
    client.close()


if __name__ == "__main__":
    asyncio.run(setup())
