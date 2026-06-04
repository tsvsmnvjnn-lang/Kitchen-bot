#!/usr/bin/env python3
"""
Кухонный бот для сотрудников.
Установка: pip install python-telegram-bot
Запуск: python kitchen_bot.py
"""

import logging
from datetime import datetime, timezone, timedelta

ALMATY_TZ = timezone(timedelta(hours=5))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8730416645:AAHFqcZmAMzrS9eoY1YBO8x2M1EhZaof_pw"  # Получить у @BotFather в Telegram

# Твой Telegram ID — будешь получать уведомления и статистику
# Узнать свой ID: написать @userinfobot в Telegram
ADMIN_ID = 528939522  # ← замени на свой ID

# ID сотрудников, которым разрешён доступ к боту.
ALLOWED_USER_IDS = [
    7265379851,   # Рома
    528939522,   # Админ

    # добавьте остальных сотрудников...
]
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Статус каждого сотрудника { user_id: {"arrived": bool, "food": "eating"/"not_eating"/None, "status": str} }
user_data: dict[int, dict] = {}

# Имена сотрудников { user_id: "Имя" }
user_names: dict[int, str] = {}


def get_user(user_id: int) -> dict:
    if user_id not in user_data:
        user_data[user_id] = {"arrived": False, "food": None, "status": "—", "break": False, "left": False}
    return user_data[user_id]


def make_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с учётом уже нажатых кнопок."""
    u = get_user(user_id)
    keyboard = []

    # Кнопка "Я пришёл" — только если ещё не нажимал сегодня
    if not u["arrived"]:
        keyboard.append([InlineKeyboardButton("✅ Я пришёл на работу", callback_data="arrived")])
    else:
        keyboard.append([InlineKeyboardButton("✅ Уже отмечен (пришёл)", callback_data="already_arrived")])

    # Кнопки еды — только если ещё не выбирал
    if u["food"] is None:
        keyboard.append([InlineKeyboardButton("🍽 Буду есть", callback_data="eating")])
        keyboard.append([InlineKeyboardButton("🚫 Не буду есть", callback_data="not_eating")])
    elif u["food"] == "eating":
        keyboard.append([InlineKeyboardButton("🍽 Уже отмечено (буду есть)", callback_data="already_food")])
    else:
        keyboard.append([InlineKeyboardButton("🚫 Уже отмечено (не буду есть)", callback_data="already_food")])

    # Перерыв и уход — всегда доступны
    keyboard.append([InlineKeyboardButton("☕ Иду на перерыв", callback_data="break")])
    keyboard.append([InlineKeyboardButton("🚪 Я ушёл", callback_data="left")])

    return InlineKeyboardMarkup(keyboard)


def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS


def reset_daily_stats():
    """Сброс статистики (вызывается вручную или можно добавить по расписанию)."""
    user_data.clear()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text(
            "⛔ У вас нет доступа к этому боту.\n"
            f"Ваш ID: <code>{user.id}</code> — передайте его администратору.",
            parse_mode="HTML",
        )
        return

    name = user.first_name or "Сотрудник"
    user_names[user.id] = name
    u = get_user(user.id)

    await update.message.reply_text(
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"Статус: <i>{u['status']}</i>\n\n"
        "Выбери действие:",
        parse_mode="HTML",
        reply_markup=make_keyboard(user.id),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user

    if not is_allowed(user.id):
        await query.answer("⛔ Нет доступа", show_alert=True)
        return

    action = query.data
    name = user.first_name or "Сотрудник"
    user_names[user.id] = name
    now = datetime.now(ALMATY_TZ).strftime("%H:%M")

    u = get_user(user.id)

    # Заблокированные повторные нажатия
    if action == "already_arrived":
        await query.answer("⚠️ Ты уже отметился как пришедший!", show_alert=True)
        return
    if action == "already_food":
        await query.answer("⚠️ Ты уже выбрал еду сегодня!", show_alert=True)
        return

    await query.answer()

    if action == "arrived":
        u["arrived"] = True
        u["status"] = f"✅ На работе (с {now})"
        reply = f"✅ <b>{name}</b>, добро пожаловать! Отметился в {now}."
        notif = f"✅ <b>{name}</b> пришёл на работу — {now}"

    elif action == "eating":
        u["food"] = "eating"
        u["status"] = f"🍽 Будет есть"
        reply = f"🍽 <b>{name}</b>, отлично! Ты будешь есть. Время: {now}."
        notif = f"🍽 <b>{name}</b> будет есть — {now}"

    elif action == "not_eating":
        u["food"] = "not_eating"
        u["status"] = f"🚫 Не будет есть"
        reply = f"🚫 <b>{name}</b>, понял! Ты не будешь есть. Время: {now}."
        notif = f"🚫 <b>{name}</b> не будет есть — {now}"

    elif action == "break":
        u["status"] = f"☕ На перерыве (с {now})"
        reply = f"☕ <b>{name}</b>, хорошего перерыва! Время: {now}."
        notif = f"☕ <b>{name}</b> ушёл на перерыв — {now}"

    elif action == "left":
        u["status"] = f"🚪 Ушёл (в {now})"
        reply = f"🚪 <b>{name}</b>, до свидания! Ушёл в {now}."
        notif = f"🚪 <b>{name}</b> ушёл — {now}"

    else:
        return

    await query.edit_message_text(
        text=f"{reply}\n\n<i>Статус: {u['status']}</i>\n\nВыбери следующее действие:",
        parse_mode="HTML",
        reply_markup=make_keyboard(user.id),
    )

    # Уведомление админу
    username = f"@{user.username}" if user.username else f"id={user.id}"
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 {notif}\n<i>{username}</i>",
        parse_mode="HTML",
    )

    logger.info(f"[{now}] {name} (id={user.id}): {action}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stats — статистика за день (только для админа)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    today = datetime.now(ALMATY_TZ).strftime("%d.%m.%Y")

    arrived = []
    eating = []
    not_eating = []
    no_food = []

    for uid, data in user_data.items():
        uname = user_names.get(uid, f"id={uid}")
        if data.get("arrived"):
            arrived.append(uname)
        food = data.get("food")
        if food == "eating":
            eating.append(uname)
        elif food == "not_eating":
            not_eating.append(uname)
        elif data.get("arrived"):
            no_food.append(uname)

    def fmt(lst): return "\n".join(f"  • {n}" for n in lst) if lst else "  —"

    text = (
        f"📊 <b>Статистика за {today}</b>\n\n"
        f"✅ <b>Пришли ({len(arrived)}):</b>\n{fmt(arrived)}\n\n"
        f"🍽 <b>Будут есть ({len(eating)}):</b>\n{fmt(eating)}\n\n"
        f"🚫 <b>Не будут есть ({len(not_eating)}):</b>\n{fmt(not_eating)}\n\n"
        f"❓ <b>Не выбрали еду ({len(no_food)}):</b>\n{fmt(no_food)}"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /reset — сброс статистики за день (только для админа)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    reset_daily_stats()
    await update.message.reply_text("♻️ Статистика сброшена. Новый день начат!")


def main() -> None:
    if BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ Сначала укажи BOT_TOKEN в начале файла!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
