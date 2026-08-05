import logging
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# ========== НАСТРОЙКИ (БЕРИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ) ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
CONTACT_USERNAME = os.environ.get("CONTACT_USERNAME")

if not BOT_TOKEN or not ADMIN_CHAT_ID or not CONTACT_USERNAME:
    print("❌ Ошибка: не заданы переменные окружения BOT_TOKEN, ADMIN_CHAT_ID, CONTACT_USERNAME")
    exit(1)

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
# ================================================================

# Загружаем товары из JSON
def load_products():
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Файл products.json не найден!")
        return {}

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать в TgUserStore!\n"
        "Здесь ты найдешь более 60+ уникальных юзернеймов.\n"
        "Выбери свой идеальный никнейм!"
    )
    keyboard = [[InlineKeyboardButton("🛒 Приступить к покупкам", callback_data="show_categories")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    products = load_products()

    # Показываем категории
    if data == "show_categories":
        keyboard = []
        for cat in products.keys():
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])
        await query.edit_message_text("Выбери категорию:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Показываем товары в категории
    elif data.startswith("cat_"):
        category = data[4:]
        items = products.get(category, {})
        keyboard = []
        for prod_id, info in items.items():
            button_text = f"{info['name']} — {info['price']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"prod_{prod_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="show_categories")])
        await query.edit_message_text(f"Товары в категории «{category}»:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Показываем способы покупки для товара
    elif data.startswith("prod_"):
        prod_id = data[5:]
        found = None
        for cat, items in products.items():
            if prod_id in items:
                found = items[prod_id]
                break
        if found:
            text = f"Товар: {found['name']}\nЦена: {found['price']}\n\nВыбери способ покупки:"
            keyboard = [
                [InlineKeyboardButton("🔗 GGSEL", url=found.get("link_ggsel", ""))],
                [InlineKeyboardButton("🔗 PLAYEROK", url=found.get("link_playerok", ""))],
                [InlineKeyboardButton("🔗 STARVELL", url=found.get("link_starvell", ""))],
                [InlineKeyboardButton("💬 Договориться лично", callback_data=f"contact_{prod_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="show_categories")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("Товар не найден.")

    # Обработка "Договориться лично"
    elif data.startswith("contact_"):
        prod_id = data[8:]
        found = None
        for cat, items in products.items():
            if prod_id in items:
                found = items[prod_id]
                break
        if found:
            user = update.effective_user
            # Уведомление админу
            admin_msg = (
                f"🔔 Пользователь хочет купить товар!\n"
                f"Товар: {found['name']}\n"
                f"Пользователь: @{user.username or 'без username'} (ID: {user.id})\n"
                f"Ссылка: tg://user?id={user.id}"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)

            # Ответ пользователю
            await query.edit_message_text(
                f"Свяжись с нами: @{CONTACT_USERNAME}\n"
                "Мы ответим в ближайшее время.\n\n"
                "Если у тебя спам-блок, нажми на кнопку ниже."
            )
            keyboard = [[InlineKeyboardButton("🚫 У меня спам-блок", callback_data=f"spam_{prod_id}")]]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Напиши нам, если не можешь написать первым.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # Обработка спам-блока
    elif data.startswith("spam_"):
        prod_id = data[5:]
        found = None
        for cat, items in products.items():
            if prod_id in items:
                found = items[prod_id]
                break
        user = update.effective_user
        admin_msg = (
            f"⚠️ У пользователя СПАМ-БЛОК!\n"
            f"Товар: {found['name'] if found else 'неизвестен'}\n"
            f"ID пользователя: {user.id}\n"
            f"Напиши ему: tg://user?id={user.id}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
        await query.edit_message_text("✅ Понял! Мы свяжемся с тобой сами в ближайшее время.")

    # Назад в главное меню
    elif data == "back_to_start":
        await start(update, context)

# ========== ЗАПУСК ==========
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
