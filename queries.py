"""
Все агрегационные запросы для 5 отчётов
"""

from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime


async def get_closed_count(col: AsyncIOMotorCollection, date_from: datetime, date_to: datetime) -> dict:
    """1. Количество закрытых жалоб за период"""
    pipeline = [
        {"$match": {
            "status": "closed",
            "closed_at": {"$gte": date_from, "$lte": date_to}
        }},
        {"$count": "total"}
    ]
    result = await col.aggregate(pipeline).to_list(1)
    return {"total": result[0]["total"] if result else 0}


async def get_resolution_time_stats(col: AsyncIOMotorCollection, date_from: datetime, date_to: datetime) -> dict:
    """2. Среднее/мин/макс время рассмотрения (в часах)"""
    pipeline = [
        {"$match": {
            "status": "closed",
            "closed_at": {"$gte": date_from, "$lte": date_to},
            "created_at": {"$exists": True}
        }},
        {"$project": {
            "complaint_number": 1,
            "title": 1,
            "assigned_to": 1,
            "hours": {
                "$divide": [
                    {"$subtract": ["$closed_at", "$created_at"]},
                    3600000  # миллисекунды → часы
                ]
            }
        }},
        {"$facet": {
            "stats": [
                {"$group": {
                    "_id": None,
                    "avg_hours": {"$avg": "$hours"},
                    "min_hours": {"$min": "$hours"},
                    "max_hours": {"$max": "$hours"},
                    "total": {"$sum": 1}
                }}
            ],
            "fastest": [
                {"$sort": {"hours": 1}},
                {"$limit": 1},
                {"$project": {"complaint_number": 1, "title": 1, "hours": 1, "assigned_to": 1}}
            ],
            "slowest": [
                {"$sort": {"hours": -1}},
                {"$limit": 1},
                {"$project": {"complaint_number": 1, "title": 1, "hours": 1, "assigned_to": 1}}
            ]
        }}
    ]
    result = await col.aggregate(pipeline).to_list(1)
    if not result:
        return {}
    data = result[0]
    stats = data["stats"][0] if data["stats"] else {}
    return {
        "avg_hours": round(stats.get("avg_hours", 0), 1),
        "min_hours": round(stats.get("min_hours", 0), 1),
        "max_hours": round(stats.get("max_hours", 0), 1),
        "total": stats.get("total", 0),
        "fastest": data["fastest"][0] if data["fastest"] else None,
        "slowest": data["slowest"][0] if data["slowest"] else None,
    }


async def get_top_closers(col: AsyncIOMotorCollection, date_from: datetime, date_to: datetime, limit: int = 10) -> list:
    """3. Кто больше всего закрыл жалоб"""
    pipeline = [
        {"$match": {
            "status": "closed",
            "closed_at": {"$gte": date_from, "$lte": date_to}
        }},
        {"$group": {
            "_id": "$assigned_to",
            "closed_count": {"$sum": 1},
            "approved": {"$sum": {"$cond": [{"$eq": ["$resolution", "approved"]}, 1, 0]}},
            "rejected": {"$sum": {"$cond": [{"$eq": ["$resolution", "rejected"]}, 1, 0]}},
        }},
        {"$sort": {"closed_count": -1}},
        {"$limit": limit},
        {"$project": {
            "employee": "$_id",
            "closed_count": 1,
            "approved": 1,
            "rejected": 1,
            "_id": 0
        }}
    ]
    return await col.aggregate(pipeline).to_list(limit)


async def get_total_by_department(col: AsyncIOMotorCollection, date_from: datetime, date_to: datetime) -> list:
    """4. Общее количество жалоб по отделам за период"""
    pipeline = [
        {"$match": {
            "created_at": {"$gte": date_from, "$lte": date_to}
        }},
        {"$group": {
            "_id": "$department",
            "total": {"$sum": 1},
            "open": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}},
            "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
            "closed": {"$sum": {"$cond": [{"$eq": ["$status", "closed"]}, 1, 0]}},
        }},
        {"$sort": {"total": -1}},
        {"$project": {
            "department": "$_id",
            "total": 1, "open": 1, "in_progress": 1, "closed": 1,
            "_id": 0
        }}
    ]
    return await col.aggregate(pipeline).to_list(50)


async def get_status_summary(col: AsyncIOMotorCollection, date_from: datetime, date_to: datetime) -> dict:
    """5. Статусы жалоб (одобрено/отказано/в работе/открыто)"""
    pipeline = [
        {"$match": {
            "created_at": {"$gte": date_from, "$lte": date_to}
        }},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "open": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}},
            "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
            "closed": {"$sum": {"$cond": [{"$eq": ["$status", "closed"]}, 1, 0]}},
            "approved": {"$sum": {"$cond": [{"$eq": ["$resolution", "approved"]}, 1, 0]}},
            "rejected": {"$sum": {"$cond": [{"$eq": ["$resolution", "rejected"]}, 1, 0]}},
        }}
    ]
    result = await col.aggregate(pipeline).to_list(1)
    return result[0] if result else {}
