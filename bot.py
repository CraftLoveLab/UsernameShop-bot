import logging
import json
import os
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
CONTACT_USERNAME = os.environ.get("CONTACT_USERNAME")
CHANNEL_ID = -1001234567890  # ⚠️ ЗАМЕНИ НА СВОЙ ID КАНАЛА

if not BOT_TOKEN or not ADMIN_CHAT_ID or not CONTACT_USERNAME:
    print("❌ Ошибка: не заданы переменные окружения")
    exit(1)

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
# ================================

# Загружаем товары
def load_products():
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Загружаем промокоды
def load_promocodes():
    try:
        with open("promocodes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Загружаем использованные промокоды
def load_used_promocodes():
    try:
        with open("used_promocodes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_used_promocodes(data):
    with open("used_promocodes.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Функция для пересчёта цены со скидкой
def apply_discount(price_text, discount_percent):
    """
    Принимает строку цены вида '1500 ₽ / 13 TON' и скидку в процентах.
    Возвращает строку с пересчитанными ценами.
    """
    if discount_percent == 0:
        return price_text
    
    # Ищем числа в тексте
    numbers = re.findall(r'(\d+[\s]?\d*)\s*(₽|TON)', price_text)
    
    result = []
    for num_str, currency in numbers:
        # Убираем пробелы из числа (если есть)
        clean_num = int(num_str.replace(' ', ''))
        # Считаем скидку
        discounted = clean_num * (100 - discount_percent) // 100
        # Форматируем с пробелом
        formatted = f"{discounted:,}".replace(',', ' ')
        result.append(f"~~{clean_num:,}~~ {formatted} {currency}".replace(',', ' '))
    
    # Собираем обратно в строку
    if result:
        return ' / '.join(result)
    return price_text

# Проверка подписки (заглушка, если не нужно)
async def check_subscription(user_id):
    return True  # Если проверка не нужна — оставляем True

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать в TgUserStore!\n"
        "Здесь ты найдешь более 60+ уникальных юзернеймов.\n"
        "Выбери свой идеальный никнейм!\n\n"
        "🎁 Чтобы получить скидку 5% на все товары, введи:\n"
        "<code>/promo 1BUYUSER</code>"
    )
    keyboard = [
        [InlineKeyboardButton("🛒 Приступить к покупкам", callback_data="show_categories")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# Обработчик команды /promo
async def promo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    promocodes = load_promocodes()
    used_promocodes = load_used_promocodes()
    
    if not args:
        await update.message.reply_text("ℹ️ Используй: /promo КОД_ПРОМОКОДА")
        return
    
    promo_key = args[0].upper()
    
    # Проверяем, существует ли такой промокод
    if promo_key not in promocodes:
        await update.message.reply_text("❌ Неверный промокод.")
        return
    
    # Проверяем, активен ли
    if not promocodes[promo_key]["active"]:
        await update.message.reply_text("❌ Этот промокод больше не активен.")
        return
    
    # Проверяем лимит использований
    if promocodes[promo_key]["used"] >= promocodes[promo_key]["max_uses"]:
        await update.message.reply_text("❌ Промокод уже использован максимальное количество раз.")
        return
    
    # Проверяем, не использовал ли уже этот пользователь
    if str(user_id) in used_promocodes:
        await update.message.reply_text("❌ Ты уже активировал промокод ранее.")
        return
    
    # Всё ок — активируем
    used_promocodes[str(user_id)] = promo_key
    save_used_promocodes(used_promocodes)
    
    # Увеличиваем счётчик
    promocodes[promo_key]["used"] += 1
    with open("promocodes.json", "w", encoding="utf-8") as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=4)
    
    discount = promocodes[promo_key]["discount"]
    await update.message.reply_text(
        f"✅ Промокод <b>{promo_key}</b> активирован!\n"
        f"Скидка {discount}% будет автоматически применяться ко всем товарам.\n\n"
        f"🛒 Переходи в каталог и выбирай товары!",
        parse_mode="HTML"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    products = load_products()
    used_promocodes = load_used_promocodes()
    
    # Получаем скидку пользователя (если есть)
    user_discount = 0
    if str(user_id) in used_promocodes:
        promo_key = used_promocodes[str(user_id)]
        promocodes = load_promocodes()
        if promo_key in promocodes:
            user_discount = promocodes[promo_key]["discount"]

    # Показать категории
    if data == "show_categories":
        keyboard = []
        for cat in products.keys():
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])
        await query.edit_message_text("Выбери категорию:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Показать товары в категории
    elif data.startswith("cat_"):
        category = data[4:]
        items = products.get(category, {})
        keyboard = []
        for prod_id, info in items.items():
            price = info['price']
            if user_discount > 0:
                price = apply_discount(info['price'], user_discount)
            button_text = f"{info['name']} — {price}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"prod_{prod_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="show_categories")])
        await query.edit_message_text(f"Товары в категории «{category}»:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Показать способы покупки
    elif data.startswith("prod_"):
        prod_id = data[5:]
        found = None
        for cat, items in products.items():
            if prod_id in items:
                found = items[prod_id]
                break
        if found:
            price_display = found['price']
            if user_discount > 0:
                price_display = apply_discount(found['price'], user_discount)
            
            discount_text = ""
            if user_discount > 0:
                discount_text = f"\n\n💥 Скидка {user_discount}% уже применена к цене!"
            
            text = f"Товар: {found['name']}\nЦена: {price_display}{discount_text}\n\nВыбери способ покупки:"
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
            username = f"@{user.username}" if user.username else "❌ нет username"
            
            admin_msg = (
                f"🔔 Пользователь хочет купить товар!\n"
                f"Товар: {found['name']}\n"
                f"Username: {username}\n"
                f"ID пользователя: {user.id}\n"
                f"Ссылка: tg://user?id={user.id}"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)

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
        username = f"@{user.username}" if user.username else "❌ нет username"
        
        admin_msg = (
            f"⚠️ У пользователя СПАМ-БЛОК!\n"
            f"Товар: {found['name'] if found else 'неизвестен'}\n"
            f"Username: {username}\n"
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
    application.add_handler(CommandHandler("promo", promo_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
