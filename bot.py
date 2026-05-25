from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters, MessageHandler
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

# НАСТРОЙКИ ВНЕШНЕГО ВИДА
SHOW_DETAILED_TEXT = False  # True = больше текста, False = компактный вид
PROJECT_NAME = "Два Дебила БОТ"  # Название вашего проекта

# =========================
# JSON STORAGE
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

async def cleanup_old_ideas(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача: удаляет идеи старше 12 часов"""
    ideas_data = load_ideas()
    now = datetime.now()
    
    # Оставляем только те, которым меньше 12 часов
    fresh_ideas = [
        idea for idea in ideas_data 
        if (now - datetime.fromisoformat(idea['timestamp'])) < timedelta(hours=12)
    ]
    
    if len(fresh_ideas) != len(ideas_data):
        save_ideas(fresh_ideas)
        print(f"🧹 Очистка: удалено {len(ideas_data) - len(fresh_ideas)} устаревших идей.")


# =========================
# KEYBOARD
# =========================


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "💡 Мои идеи",
                callback_data="my_ideas"
            ),
            InlineKeyboardButton(
                "📖 Помощь",
                callback_data="help"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def back_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ Назад в меню",
                callback_data="start"
            )
        ]
    ])


# =========================
# COMMANDS
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"👋 <b>Добро пожаловать в {PROJECT_NAME}!</b>\n\n"
        f"Этот бот создан для сбора и обработки ваших предложений. "
        f"Мы внимательно изучаем каждую идею!\n\n"
        f"<b>Доступные функции:</b>\n"
        f"💡 <code>/idea [текст]</code> — предложить идею\n"
        f"📂 <code>/my_ideas</code> — проверить статус своих идей\n"
        f"❓ <code>/help</code> — подробная информация\n\n"
        f"<i>Просто введите команду ниже или воспользуйтесь кнопками:</i>"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu(), parse_mode=ParseMode.HTML)
        return

    message = update.effective_message
    if message:
        await message.reply_text(text, reply_markup=main_menu(), parse_mode=ParseMode.HTML)




async def idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    
    if not message:
        return
    
    if not context.args:
        await message.reply_text(
            "❌ <b>Ошибка:</b> вы не написали текст идеи!\n\n"
            "<b>Пример:</b> <code>/idea Сделать темную тему</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    idea_text = " ".join(context.args)
    chat_id = update.effective_chat.id
    user_id = user.id if user else update.effective_chat.id
    username = user.username if user else "Channel"
    first_name = user.first_name if user else update.effective_chat.title
    
    ideas_data = load_ideas()
    
    # Проверка на дубликат текста (опционально)
    if any(i['text'] == idea_text and i['user_id'] == user_id for i in ideas_data):
        await message.reply_text("⚠️ Вы уже предлагали точно такую же идею.")
        return

    new_idea = {
        "id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username or "нет",
        "first_name": first_name or "Пользователь",
        "text": idea_text,
        "timestamp": datetime.now().isoformat(),
        "status": "новая"
    }
    
    ideas_data.append(new_idea)
    save_ideas(ideas_data)
    
    await message.reply_text(
        f"🚀 <b>Идея успешно отправлена!</b>\n\n"
        f"📝 <i>{idea_text}</i>\n\n"
        f"Вы получите уведомление, когда администратор рассмотрит её.",
        parse_mode=ParseMode.HTML
    )
    
    try:
        is_channel = "Канал" if not user else "Пользователь"
        admin_text = (
            f"<b>📬 Новое предложение!</b>\n\n"
            f"💭 <i>{idea_text}</i>\n\n"
            f"🔹 <b>От кого:</b> {first_name} (@{username})\n"
            f"🔹 <b>Тип:</b> {is_channel} | ID: <code>{user_id}</code>"
        )
        
        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Принять", callback_data=f"approve_{new_idea['id']}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{new_idea['id']}")
            ]
        ])
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=admin_keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Ошибка: {e}")




async def my_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return
    
    if update.callback_query:
        await update.callback_query.answer()
    
    user_id = update.effective_user.id if update.effective_user else update.effective_chat.id
    ideas_data = load_ideas()
    user_ideas = [idea for idea in ideas_data if idea["user_id"] == user_id]
    
    if not user_ideas:
        text = "📭 <b>У вас пока нет активных предложений.</b>\n\nСамое время что-нибудь предложить! Используйте команду /idea."
    else:
        text = f"💡 <b>Ваши идеи (Всего: {len(user_ideas)})</b>\n\n"
        for idx, idea in enumerate(user_ideas, 1):
            status_emoji = "⏳" if idea['status'] == "новая" else "✅" if idea['status'] == "принята" else "❌"
            date_str = idea['timestamp'][:10]
            text += f"{idx}. <b>{idea['text']}</b>\n   Статус: {status_emoji} {idea['status']} | {date_str}\n\n"
    
    await message.reply_text(text, reply_markup=back_menu(), parse_mode=ParseMode.HTML)




async def all_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Только в личном чате!
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
        
        if update.effective_chat.type != "private":
            await query.answer("⚠️ Только в личном чате!", show_alert=True)
            return
        
        if update.effective_user.id != ADMIN_ID:
            await query.answer("❌ Нет доступа", show_alert=True)
            return
    else:
        message = update.message
        
        if update.effective_chat.type != "private":
            await message.reply_text("⚠️ Используйте в личном чате с ботом", parse_mode=ParseMode.HTML)
            return
        
        if update.effective_user.id != ADMIN_ID:
            await message.reply_text("❌ Нет доступа", parse_mode=ParseMode.HTML)
            return
    
    ideas_data = load_ideas()
    if not ideas_data:
        await message.reply_text("📭 <b>Список идей пуст.</b>", parse_mode=ParseMode.HTML)
        return

    # 1. Сводная статистика
    total = len(ideas_data)
    new_count = sum(1 for i in ideas_data if i['status'] == "новая")
    summary = (
        f"📋 <b>Статистика за 12 часов:</b>\n"
        f"📊 Всего в базе: {total}\n"
        f"⏳ Ожидают решения: {new_count}\n"
        f"───────────────────"
    )
    await message.reply_text(summary, parse_mode=ParseMode.HTML)

    # 2. Показываем новые идеи с кнопками для управления
    for idea in ideas_data:
        if idea['status'] == "новая":
            text = (
                f"⏳ <b>ID:</b> <code>{idea['id'][:8]}</code>\n"
                f"💭 <i>{idea['text']}</i>\n\n"
                f"👤 {idea['first_name']} (@{idea['username']})\n"
                f"📅 {idea['timestamp'][11:16]} (МСК/UTC)"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Принять", callback_data=f"approve_{idea['id']}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{idea['id']}")
                ]
            ])
            await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await message.reply_text("✨ <i>Это все актуальные идеи на текущий момент.</i>", 
                             parse_mode=ParseMode.HTML, reply_markup=back_menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    
    if not message:
        return
    
    if update.callback_query:
        await update.callback_query.answer()
    
    text = (
        f"❓ <b>Как пользоваться ботом?</b>\n\n"
        f"1️⃣ <b>Отправка идеи:</b> Введите команду <code>/idea</code> и через пробел ваше предложение.\n"
        f"2️⃣ <b>Просмотр:</b> Команда <code>/my_ideas</code> покажет все ваши предложения и их текущий статус.\n"
        f"3️⃣ <b>Уведомления:</b> Когда администратор изменит статус вашей идеи, бот пришлет вам сообщение.\n\n"
        f"📍 Бот работает в личных сообщениях, группах и каналах."
    )
    
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=back_menu())


# =========================
# APPROVE/REJECT IDEAS
# =========================

async def handle_admin_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перехватывает текстовый ответ админа для комментария к идее"""
    if update.effective_user.id != ADMIN_ID or 'pending_idea' not in context.user_data:
        return

    pending = context.user_data.pop('pending_idea')
    idea_id = pending['id']
    action = pending['action']
    comment = update.message.text

    # Удаляем сообщение с просьбой о комментарии для чистоты
    try:
        await context.bot.delete_message(chat_id=ADMIN_ID, message_id=pending['msg_id'])
    except:
        pass

    if action == "approve":
        await approve_idea(update, context, idea_id, comment)
    else:
        await reject_idea(update, context, idea_id, comment)


async def approve_idea(update: Update, context: ContextTypes.DEFAULT_TYPE, idea_id: str, comment: str = None):
    ideas_data = load_ideas()
    idea_obj = next((i for i in ideas_data if i["id"] == idea_id), None)
    
    if not idea_obj:
        msg = "❌ Идея не найдена"
        if update.callback_query: await update.callback_query.edit_message_text(msg)
        else: await update.message.reply_text(msg)
        return
    
    idea_obj["status"] = "принята"
    if comment:
        idea_obj["admin_comment"] = comment
    save_ideas(ideas_data)
    
    status_text = (
        f"✅ <b>Статус: ОДОБРЕНО</b>\n"
        f"───────────────────\n"
        f"💭 <i>{idea_obj['text']}</i>\n"
        f"───────────────────\n"
        f"👤 От: {idea_obj['first_name']} (@{idea_obj['username']})\n"
        f"💬 Ответ: {comment or '<i>Администратор принял вашу идею</i>'}"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(status_text, parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=ADMIN_ID, text=status_text, parse_mode=ParseMode.HTML)
    
    # Уведомление пользователя
    try:
        target_chat_id = idea_obj.get('chat_id', idea_obj['user_id'])
        # Добавляем упоминание, если это группа (чтобы автор понял, что это ему)
        mention = f"👤 <b>{idea_obj['first_name']}</b>, " if target_chat_id != idea_obj['user_id'] else ""
        
        user_msg = (
            f"{mention}✅ <b>Ваша идея одобрена!</b>\n\n"
            f"📝 <i>{idea_obj['text']}</i>\n\n"
            f"💬 <b>Ответ:</b> {comment or 'Администратор принял вашу идею'}"
        )
        await context.bot.send_message(
            chat_id=target_chat_id, text=user_msg, parse_mode=ParseMode.HTML
        )
    except:
        pass


async def reject_idea(update: Update, context: ContextTypes.DEFAULT_TYPE, idea_id: str, comment: str = None):
    ideas_data = load_ideas()
    idea_obj = next((i for i in ideas_data if i["id"] == idea_id), None)
    
    if not idea_obj:
        msg = "❌ Идея не найдена"
        if update.callback_query: await update.callback_query.edit_message_text(msg)
        else: await update.message.reply_text(msg)
        return
    
    idea_obj["status"] = "отклонена"
    if comment:
        idea_obj["admin_comment"] = comment
    save_ideas(ideas_data)
    
    status_text = (
        f"❌ <b>Статус: ОТКЛОНЕНО</b>\n"
        f"───────────────────\n"
        f"💭 <i>{idea_obj['text']}</i>\n"
        f"───────────────────\n"
        f"👤 От: {idea_obj['first_name']} (@{idea_obj['username']})\n"
        f"💬 Ответ: {comment or '<i>Идея отклонена администратором</i>'}"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(status_text, parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=ADMIN_ID, text=status_text, parse_mode=ParseMode.HTML)
    
    # Уведомление пользователя
    try:
        target_chat_id = idea_obj.get('chat_id', idea_obj['user_id'])
        # Добавляем упоминание, если это группа
        mention = f"👤 <b>{idea_obj['first_name']}</b>, " if target_chat_id != idea_obj['user_id'] else ""
        
        user_msg = (
            f"{mention}❌ <b>Ваша идея не одобрена</b>\n\n"
            f"📝 <i>{idea_obj['text']}</i>\n\n"
            f"💬 <b>Ответ:</b> {comment or 'Администратор отклонил вашу идею'}"
        )
        await context.bot.send_message(
            chat_id=target_chat_id, text=user_msg, parse_mode=ParseMode.HTML
        )
    except:
        pass

# =========================
# CALLBACK HANDLER
# =========================


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "start":
        await start(update, context)
    
    elif data == "my_ideas":
        await my_ideas(update, context)
    
    elif data == "all_ideas":
        await all_ideas(update, context)
    
    elif data == "help":
        await help_command(update, context)
    
    elif data.startswith("approve_"):
        idea_id = data.split("_", 1)[1]
        context.user_data['pending_idea'] = {'id': idea_id, 'action': 'approve', 'msg_id': query.message.message_id}
        await query.edit_message_text(
            "📝 <b>Добавить комментарий к ОДОБРЕНИЮ?</b>\n\nОтправьте текст ответа боту.\n"
            "<i>Если комментарий не нужен, нажмите кнопку ниже.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏩ Пропустить", callback_data=f"skip_approve_{idea_id}")]])
        )
    
    elif data.startswith("reject_"):
        idea_id = data.split("_", 1)[1]
        context.user_data['pending_idea'] = {'id': idea_id, 'action': 'reject', 'msg_id': query.message.message_id}
        await query.edit_message_text(
            "📝 <b>Добавить причину ОТКЛОНЕНИЯ?</b>\n\nОтправьте текст ответа боту.\n"
            "<i>Если комментарий не нужен, нажмите кнопку ниже.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏩ Пропустить", callback_data=f"skip_reject_{idea_id}")]])
        )

    elif data.startswith("skip_"):
        parts = data.split("_")
        action, idea_id = parts[1], parts[2]
        context.user_data.pop('pending_idea', None)
        if action == "approve": await approve_idea(update, context, idea_id)
        else: await reject_idea(update, context, idea_id)
    
    else:
        await query.answer()


# =========================
# MAIN
# =========================


async def set_commands(app):
    """Устанавливает список команд для показа при вводе /"""
    commands = [
        BotCommand("start", "Главное меню"),
        BotCommand("idea", "Отправить идею администратору"),
        BotCommand("my_ideas", "Просмотреть свои идеи"),
        BotCommand("all_ideas", "Все идеи (админ)"),
        BotCommand("help", "Справка и помощь")
    ]
    await app.bot.set_my_commands(commands)


def main():
    app = Application.builder().token(TOKEN).build()
    
    # Handlers for messages and channel posts
    app.add_handler(CommandHandler("start", start, filters=filters.ALL))
    app.add_handler(CommandHandler("idea", idea, filters=filters.ALL))
    app.add_handler(CommandHandler("my_ideas", my_ideas, filters=filters.ALL))
    app.add_handler(CommandHandler("all_ideas", all_ideas, filters=filters.ALL))
    app.add_handler(CommandHandler("help", help_command, filters=filters.ALL))
    
    # Callback for buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Handler for admin comments (text messages from admin)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(ADMIN_ID), handle_admin_comment))
    
    # Set commands before polling
    async def post_init(application):
        await set_commands(application)
        # Запуск задачи очистки раз в час (3600 секунд)
        application.job_queue.run_repeating(cleanup_old_ideas, interval=3600, first=10)
    
    app.post_init = post_init
    
    print("✅ Бот запущен!")
    print(f"Admin ID: {ADMIN_ID}")
    print("📋 Команды установлены")
    
    app.run_polling()


if __name__ == "__main__":
    main()
