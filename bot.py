"""
Telegram-бот для аналитики жалоб
Запуск: python bot.py
"""

import logging
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes
)
from queries import (
    get_closed_count, get_resolution_time_stats,
    get_top_closers, get_total_by_department, get_status_summary
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "8882563221:AAG9kSWxn4SrJIWE9cEiK3SIpYWQqXF9ymo")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://testacc:DB0Uzp4Myu8qLwod@cluster0.kuwhy7o.mongodb.net/?appName=Cluster0")
DB_NAME = "complaints_db"

# Состояния диалога выбора дат
CHOOSE_REPORT, ENTER_DATE_FROM, ENTER_DATE_TO = range(3)

REPORT_LABELS = {
    "closed_count":   "📦 Закрытые жалобы за период",
    "avg_time":       "⏱ Время рассмотрения",
    "top_closers":    "🏆 Рейтинг сотрудников",
    "by_department":  "🏢 По отделам",
    "statuses":       "📊 Статусы жалоб",
}


def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(label, callback_data=key)]
        for key, label in REPORT_LABELS.items()
    ]
    return InlineKeyboardMarkup(buttons)


def format_hours(h: float) -> str:
    if h < 24:
        return f"{h:.1f} ч"
    return f"{h/24:.1f} дн ({h:.0f} ч)"


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Аналитика жалоб*\n\nВыберите отчёт:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return CHOOSE_REPORT


async def on_report_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctx.user_data["report"] = query.data
    await query.edit_message_text(
        f"📅 Выбран: *{REPORT_LABELS[query.data]}*\n\n"
        "Введите дату начала периода в формате `ДД.ММ.ГГГГ`\n"
        "Например: `01.01.2024`",
        parse_mode="Markdown"
    )
    return ENTER_DATE_FROM


async def on_date_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ctx.user_data["date_from"] = datetime.strptime(update.message.text.strip(), "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите дату как `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return ENTER_DATE_FROM

    await update.message.reply_text(
        "📅 Введите дату окончания периода в формате `ДД.ММ.ГГГГ`",
        parse_mode="Markdown"
    )
    return ENTER_DATE_TO


async def on_date_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        date_to = datetime.strptime(update.message.text.strip(), "%d.%m.%Y")
        date_to = date_to.replace(hour=23, minute=59, second=59)
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите дату как `ДД.ММ.ГГГГ`", parse_mode="Markdown")
        return ENTER_DATE_TO

    date_from = ctx.user_data["date_from"]
    report = ctx.user_data["report"]

    if date_to < date_from:
        await update.message.reply_text("❌ Дата окончания не может быть раньше даты начала.")
        return ENTER_DATE_TO

    col = ctx.bot_data["col"]
    period = f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"

    await update.message.reply_text("⏳ Считаю данные...")

    try:
        text = await build_report(report, col, date_from, date_to, period)
    except Exception as e:
        logger.error(e)
        text = f"❌ Ошибка при получении данных: {e}"

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ В главное меню", callback_data="__menu__")
        ]])
    )
    return CHOOSE_REPORT


async def build_report(report: str, col, date_from, date_to, period: str) -> str:
    if report == "closed_count":
        data = await get_closed_count(col, date_from, date_to)
        return (
            f"📦 *Закрытые жалобы*\n"
            f"📅 Период: {period}\n\n"
            f"✅ Закрыто жалоб: *{data['total']}*"
        )

    elif report == "avg_time":
        data = await get_resolution_time_stats(col, date_from, date_to)
        if not data or data.get("total", 0) == 0:
            return f"⏱ *Время рассмотрения*\n📅 {period}\n\nДанных нет."
        fastest = data.get("fastest")
        slowest = data.get("slowest")
        lines = [
            f"⏱ *Время рассмотрения жалоб*",
            f"📅 Период: {period}",
            f"Жалоб проанализировано: {data['total']}\n",
            f"📊 Среднее время: *{format_hours(data['avg_hours'])}*",
            f"🚀 Минимальное: *{format_hours(data['min_hours'])}*",
            f"🐢 Максимальное: *{format_hours(data['max_hours'])}*",
        ]
        if fastest:
            lines.append(f"\n✅ Самая быстрая: `{fastest['complaint_number']}` — {format_hours(fastest['hours'])}")
            lines.append(f"   👤 {fastest.get('assigned_to', '—')}")
        if slowest:
            lines.append(f"\n⏳ Самая долгая: `{slowest['complaint_number']}` — {format_hours(slowest['hours'])}")
            lines.append(f"   👤 {slowest.get('assigned_to', '—')}")
        return "\n".join(lines)

    elif report == "top_closers":
        data = await get_top_closers(col, date_from, date_to)
        if not data:
            return f"🏆 *Рейтинг сотрудников*\n📅 {period}\n\nДанных нет."
        lines = [f"🏆 *Рейтинг по закрытым жалобам*", f"📅 Период: {period}\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(data):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(
                f"{medal} *{row['employee']}* — {row['closed_count']} жалоб "
                f"(✅ {row['approved']} / ❌ {row['rejected']})"
            )
        return "\n".join(lines)

    elif report == "by_department":
        data = await get_total_by_department(col, date_from, date_to)
        if not data:
            return f"🏢 *По отделам*\n📅 {period}\n\nДанных нет."
        total_all = sum(r["total"] for r in data)
        lines = [f"🏢 *Жалобы по отделам*", f"📅 Период: {period}", f"Всего: *{total_all}*\n"]
        for row in data:
            pct = round(row["total"] / total_all * 100) if total_all else 0
            lines.append(
                f"*{row['department']}*: {row['total']} ({pct}%)\n"
                f"  🔵 Открыто: {row['open']}  🟡 В работе: {row['in_progress']}  ✅ Закрыто: {row['closed']}"
            )
        return "\n".join(lines)

    elif report == "statuses":
        data = await get_status_summary(col, date_from, date_to)
        if not data or data.get("total", 0) == 0:
            return f"📊 *Статусы жалоб*\n📅 {period}\n\nДанных нет."
        total = data.get("total", 0)
        closed = data.get("closed", 0)
        return (
            f"📊 *Статусы жалоб*\n"
            f"📅 Период: {period}\n\n"
            f"📋 Всего жалоб: *{total}*\n\n"
            f"🔵 Открыто: *{data.get('open', 0)}*\n"
            f"🟡 В работе: *{data.get('in_progress', 0)}*\n"
            f"✅ Закрыто: *{closed}*\n\n"
            f"Из закрытых:\n"
            f"  ✔️ Одобрено: *{data.get('approved', 0)}*\n"
            f"  ✖️ Отказано: *{data.get('rejected', 0)}*"
        )

    return "Неизвестный отчёт"


async def on_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👋 *Аналитика жалоб*\n\nВыберите отчёт:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return CHOOSE_REPORT


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. Введите /start для нового запроса.")
    return ConversationHandler.END


def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    col = db["complaints"]

    app = ApplicationBuilder().token(TOKEN).build()
    app.bot_data["col"] = col

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(on_menu_callback, pattern="^__menu__$"),
        ],
        states={
            CHOOSE_REPORT: [
                CallbackQueryHandler(on_report_chosen, pattern="^(closed_count|avg_time|top_closers|by_department|statuses)$"),
                CallbackQueryHandler(on_menu_callback, pattern="^__menu__$"),
            ],
            ENTER_DATE_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_date_from)],
            ENTER_DATE_TO:   [MessageHandler(filters.TEXT & ~filters.COMMAND, on_date_to)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
