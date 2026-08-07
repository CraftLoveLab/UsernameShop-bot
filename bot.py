import logging
import json
import os
import re
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
CONTACT_USERNAME = os.environ.get("CONTACT_USERNAME")

if not BOT_TOKEN or not ADMIN_CHAT_ID or not CONTACT_USERNAME:
    print("❌ Ошибка: не заданы переменные окружения BOT_TOKEN, ADMIN_CHAT_ID, CONTACT_USERNAME")
    exit(1)

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
# =================================

# Загружаем товары
def load_products():
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Файл products.json не найден!")
        return {}

# Загружаем статистику просмотров
def load_stats():
    try:
        with open("stats.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Сохраняем статистику
def save_stats(stats):
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

# Увеличиваем счётчик просмотров
def increment_views(product_id):
    stats = load_stats()
    if product_id in stats:
        stats[product_id] += 1
    else:
        stats[product_id] = 1
    save_stats(stats)
    return stats[product_id]

# Применяем скидку
def apply_discount(price_text, discount_percent=25):
    pattern = r'([\d\s]+)\s*(₽|TON)'
    matches = re.findall(pattern, price_text)
    if not matches:
        return price_text
    result = []
    for num_str, currency in matches:
        clean_num = int(num_str.replace(' ', ''))
        discounted = clean_num * (100 - discount_percent) // 100
        formatted = f"{discounted:,}".replace(',', ' ')
        result.append(f"{formatted} {currency} (скидка {discount_percent}%)")
    return ' / '.join(result) if result else price_text

# Таймер
def get_time_left():
    end_date = datetime(2026, 8, 14, 6, 0, 0)
    now = datetime.now()
    if now >= end_date:
        return "❌ Акция завершена!"
    diff = end_date - now
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(f"{days} дн")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} мин")
    return " ".join(parts) if parts else "менее минуты"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    time_left = get_time_left()
    welcome_text = (
        f"✨ <b>Привет, {user.first_name}!</b> ✨\n\n"
        "Добро пожаловать в <b>TgUserStore</b> — твой личный каталог премиальных юзернеймов для Telegram.\n\n"
        "❓ <b>Почему юзернейм — это важно?</b>\n"
        "Юзернейм — это твой цифровой паспорт. Это первое, что видят люди, когда ты пишешь им. Это твой бренд, твоя визитка, твоё лицо в мире Telegram.\n\n"
        "🔥 <b>Примеры из жизни:</b>\n"
        "• Юзернейм @car продали за <b>$100 000</b>\n"
        "• @bank — за <b>$50 000</b>\n"
        "• Короткие имена — это статус, который работает на тебя 24/7\n\n"
        "💎 <b>Почему стоит купить у нас?</b>\n"
        "• Более 60+ уникальных ников — от коротких до тематических\n"
        "• Все юзы проверены и готовы к передаче\n"
        "• Полная безопасность сделки через проверенные площадки\n"
        "• Передача юзернейма каналом — быстро и надёжно\n\n"
        "🎁 <b>🔥 НЕДЕЛЯ СКИДОК!</b>\n"
        f"⏳ <b>Осталось:</b> {time_left}\n"
        "Скидка <b>25%</b> на ВСЕ юзернеймы! Цены уже пересчитаны.\n"
        "Успей выбрать свой идеальный ник! ⏳"
    )
    keyboard = [
        [InlineKeyboardButton("🛒 ПРИСТУПИТЬ К ПОКУПКАМ", callback_data="show_categories")],
        [InlineKeyboardButton("📢 Наш канал с новинками", url="https://t.me/EliteTGUsername")]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    products = load_products()
    DISCOUNT = 25

    if data == "show_categories":
        time_left = get_time_left()
        keyboard = []
        for cat in products.keys():
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])
        await query.edit_message_text(
            f"📂 <b>Выбери категорию:</b>\n\n⏳ <b>Осталось:</b> {time_left}\n🎁 Скидка <b>25%</b>!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data.startswith("cat_"):
        category = data[4:]
        items = products.get(category, {})
        stats = load_stats()
        keyboard = []
        for prod_id, info in items.items():
            discounted_price = apply_discount(info['price'], DISCOUNT)
            views = stats.get(prod_id, 0)
            button_text = f"{info['name']} — {discounted_price} 👁️{views}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"prod_{prod_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="show_categories")])
        await query.edit_message_text(
            f"📦 <b>Товары в категории «{category}»:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data.startswith("prod_"):
        prod_id = data[5:]
        found = None
        for cat, items in products.items():
            if prod_id in items:
                found = items[prod_id]
                break
        if found:
            views = increment_views(prod_id)
            discounted_price = apply_discount(found['price'], DISCOUNT)
            text = (
                f"💎 <b>{found['name']}</b>\n\n"
                f"💰 <b>Цена со скидкой 25%:</b>\n{discounted_price}\n\n"
                f"👁️ <b>Просмотров:</b> {views}\n\n"
                f"<i>Выбери способ покупки:</i>"
            )
            keyboard = [
                [InlineKeyboardButton("🔗 GGSEL", url=found.get("link_ggsel", ""))],
                [InlineKeyboardButton("🔗 PLAYEROK", url=found.get("link_playerok", ""))],
                [InlineKeyboardButton("🔗 STARVELL", url=found.get("link_starvell", ""))],
                [InlineKeyboardButton("💬 Договориться лично", callback_data=f"contact_{prod_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="show_categories")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Товар не найден.")

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
                f"Username: {username}\nID: {user.id}\nСсылка: tg://user?id={user.id}"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
            await query.edit_message_text(
                f"💬 <b>Свяжись с нами:</b> @{CONTACT_USERNAME}\n\nМы ответим.\n\n🚫 Если спам-блок — нажми ниже.",
                parse_mode="HTML"
            )
            keyboard = [[InlineKeyboardButton("🚫 У меня спам-блок", callback_data=f"spam_{prod_id}")]]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Нажми, если не можешь написать первым:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

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
            f"⚠️ <b>СПАМ-БЛОК!</b>\n"
            f"Товар: {found['name'] if found else 'неизвестен'}\n"
            f"Username: {username}\nID: {user.id}\nНапиши: tg://user?id={user.id}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode="HTML")
        await query.edit_message_text("✅ <b>Понял!</b>\n\nМы свяжемся сами.", parse_mode="HTML")

    elif data == "back_to_start":
        await start(update, context)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
