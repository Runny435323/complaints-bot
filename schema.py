"""
Схема коллекции 'complaints' в MongoDB
======================================
Пример документа:
{
    "_id": ObjectId("..."),
    "complaint_number": "CMP-2024-001",       # уникальный номер жалобы
    "title": "Проблема с оборудованием",        # краткое название
    "description": "Подробное описание...",     # полное описание
    "department": "IT",                         # отдел (IT, HR, Finance, Operations, ...)
    "status": "closed",                         # open | in_progress | closed
    "resolution": "approved",                   # approved | rejected | None (если не закрыта)
    "priority": "high",                         # low | medium | high
    "created_at": ISODate("2024-01-15T09:00:00"),
    "updated_at": ISODate("2024-01-20T14:30:00"),
    "closed_at": ISODate("2024-01-20T14:30:00"),  # None если не закрыта
    "assigned_to": "Иванов Иван",               # ответственный сотрудник
    "created_by": "Петров Пётр",                # кто подал жалобу
}

Индексы (создаются в db_setup.py):
- complaint_number: unique
- status + closed_at: для фильтрации закрытых по дате
- department: для группировки
- assigned_to: для рейтинга сотрудников
- created_at: для общей статистики по периоду
"""
