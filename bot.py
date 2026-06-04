#!/usr/bin/env python3
"""
Кухонный бот для сотрудников.
Установка: pip install python-telegram-bot
Запуск: python kitchen_bot.py
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8730416645:AAHFqcZmAMzrS9eoY1YBO8x2M1EhZaof_pw"  # Получить у @BotFather в Telegram

# Твой Telegram ID — будешь получать уведомления о каждом действии
# Узнать свой ID: написать @userinfobot в Telegram
ADMIN_ID = 528939522  # ← замени на свой ID

# ID сотрудников, которым разрешён доступ к боту.
ALLOWED_USER_IDS = [
    7265379851,   # Рома
    528939522, # Админ

    # добавьте остальных сотрудников...
]
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Храним статус каждого сотрудника { user_id: "статус" }
user_status: dict[int, str] = {}


def main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура с кнопками."""
    keyboard = [
        [InlineKeyboardButton("✅ Я пришёл на работу", callback_data="arrived")],
        [InlineKeyboardButton("🍽 Буду есть (заказать еду)", callback_data="eating")],
        [InlineKeyboardButton("☕ Иду на перерыв", callback_data="break")],
        [InlineKeyboardButton("🚪 Я ушёл", callback_data="left")],
    ]
    return InlineKeyboardMarkup(keyboard)


def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start — показывает меню."""
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text(
            "⛔ У вас нет доступа к этому боту.\n"
            f"Ваш ID: <code>{user.id}</code> — передайте его администратору.",
            parse_mode="HTML",
        )
        return

    name = user.first_name or "сотрудник"
    status = user_status.get(user.id, "—")
    await update.message.reply_text(
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"Текущий статус: <i>{status}</i>\n\n"
        "Выбери действие:",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий на кнопки."""
    query = update.callback_query
    user = query.from_user

    if not is_allowed(user.id):
        await query.answer("⛔ Нет доступа", show_alert=True)
        return

    await query.answer()  # убирает "часики" на кнопке

    now = datetime.now().strftime("%H:%M")
    name = user.first_name or "Сотрудник"

    actions = {
        "arrived": ("✅ На работе",       f"✅ <b>{name}</b>, добро пожаловать! Ты отметился в {now}."),
        "eating":  ("🍽 Буду есть",       f"🍽 <b>{name}</b>, заказ принят! Ты будешь есть. Время: {now}."),
        "break":   ("☕ На перерыве",     f"☕ <b>{name}</b>, хорошего перерыва! Время: {now}."),
        "left":    ("🚪 Ушёл",           f"🚪 <b>{name}</b>, до свидания! Ты ушёл в {now}."),
    }

    action = query.data
    if action not in actions:
        return

    status_text, reply_text = actions[action]
    user_status[user.id] = f"{status_text} (с {now})"

    await query.edit_message_text(
        text=f"{reply_text}\n\n<i>Текущий статус: {status_text}</i>\n\nВыбери следующее действие:",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

    # Уведомление админу
    username = f"@{user.username}" if user.username else f"id={user.id}"
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 <b>{name}</b> ({username})\n{status_text} — {now}",
        parse_mode="HTML",
    )

    logger.info(f"[{now}] {name} (id={user.id}): {status_text}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /status — показывает текущий статус."""
    user = update.effective_user
    if not is_allowed(user.id):
        return

    status = user_status.get(user.id, "Статус не установлен")
    await update.message.reply_text(
        f"📋 Твой статус: <b>{status}</b>",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


def main() -> None:
    if BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ Сначала укажи BOT_TOKEN в начале файла!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
