from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

import json
import os
from datetime import datetime, timedelta
import uuid

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5469826586
IDEAS_FILE = "ideas.json"

SHOW_DETAILED_TEXT = False
PROJECT_NAME = "Два Дебила БОТ"


if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в Render Environment Variables")


# =========================
# STORAGE
# =========================

def load_ideas():
    if not os.path.exists(IDEAS_FILE):
        return []
    try:
        with open(IDEAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_ideas(data):
    with open(IDEAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# =========================
# KEYBOARDS
# =========================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💡 Мои идеи", callback_data="my_ideas"),
            InlineKeyboardButton("📖 Помощь", callback_data="help")
        ]
    ])


def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="start")]
    ])


# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"👋 Добро пожаловать в {PROJECT_NAME}!"
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=main_menu())
    else:
        await update.message.reply_text(text, reply_markup=main_menu())


async def idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Используй: /idea текст")
        return

    idea_text = " ".join(context.args)
    user = update.effective_user

    ideas = load_ideas()

    new_idea = {
        "id": str(uuid.uuid4()),
        "user_id": user.id,
        "username": user.username or "none",
        "first_name": user.first_name or "user",
        "text": idea_text,
        "timestamp": datetime.now().isoformat(),
        "status": "новая"
    }

    ideas.append(new_idea)
    save_ideas(ideas)

    await update.message.reply_text("✅ Идея отправлена!")


    # уведомление админа
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"💡 Новая идея:\n{idea_text}"
        )
    except:
        pass


async def my_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ideas = load_ideas()

    user_ideas = [i for i in ideas if i["user_id"] == user_id]

    if not user_ideas:
        await update.message.reply_text("📭 Идей нет")
        return

    text = "💡 Ваши идеи:\n\n"
    for i in user_ideas:
        text += f"- {i['text']} ({i['status']})\n"

    await update.message.reply_text(text, reply_markup=back_menu())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Используй /idea текст")


# =========================
# CALLBACKS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start":
        await start(update, context)

    elif query.data == "my_ideas":
        await my_ideas(update, context)

    elif query.data == "help":
        await help_command(update, context)


# =========================
# MAIN
# =========================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("idea", idea))
    app.add_handler(CommandHandler("my_ideas", my_ideas))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
