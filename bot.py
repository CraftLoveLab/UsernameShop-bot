import logging
import json
import os
import re
import requests
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from stats_storage import increment_views, init_stats, load_stats

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

# ========== ПАРСИНГ FRAGMENT ==========
def parse_fragment_auction(username):
    """
    Парсит страницу аукциона на Fragment и возвращает данные.
    Возвращает dict с полями: current_bid, bids_count, time_left, status
    """
    url = f"https://fragment.com/username/{username}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        html = response.text
        
        # Пытаемся найти текущую ставку
        bid_pattern = r'(\d+)\s*TON'
        bids = re.findall(bid_pattern, html)
        
        # Пытаемся найти количество ставок
        bids_count_pattern = r'(\d+)\s*bids'
        bids_count = re.findall(bids_count_pattern, html)
        
        # Пытаемся найти статус аукциона
        if "Auction will close soon" in html:
            status = "🟢 Аукцион активен"
        elif "Auction will start after you place the first bid" in html:
            status = "⏳ Ожидает первой ставки"
        elif "Auction ended" in html or "Sold" in html:
            status = "🔴 Аукцион завершён"
        else:
            status = "🟡 Информация уточняется"
        
        # Текущая ставка (первое найденное число)
        current_bid = bids[0] if bids else "0"
        
        # Количество ставок
        bids_count_val = bids_count[0] if bids_count else "0"
        
        return {
            "current_bid": current_bid,
            "bids_count": bids_count_val,
            "status": status,
            "url": url
        }
    except Exception as e:
        print(f"⚠️ Ошибка парсинга {username}: {e}")
        return None

# Применяем скидку
def apply_discount(price_text, discount_percent=25):
    if not is_discount_active():
        return price_text
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

def is_discount_active():
    end_date = datetime(2026, 8, 14, 6, 0, 0)
    return datetime.now() < end_date

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
    discount_active = is_discount_active()
    
    welcome_text = (
        f"✨ <b>Привет, {user.first_name}!</b> ✨\n\n"
        "Добро пожаловать в <b>TgUserStore</b> — твой личный каталог премиальных юзернеймов для Telegram.\n\n"
        "❓ <b>Почему юзернейм — это важно?</b>\n"
        "Юзернейм — это твой цифровой паспорт. Это первое, что видят люди, когда ты пишешь им. Это твой бренд, твоя визитка, твоё лицо в мире Telegram.\n\n"
        "🔥 <b>Примеры из жизни:</b>\n"
        "• Юзернейм @danbao продали за <b>$2,1–$2,2 млн / 1 583 948 TON</b>\n"
        "• @bank — за <b>~$1.34 млн / 850,000 TON</b>\n"
        "• Короткие имена — это статус, который работает на тебя 24/7\n\n"
        "💎 <b>Почему стоит купить у нас?</b>\n"
        "• Более 80+ уникальных ников — от коротких до тематических\n"
        "• Все юзы проверены и готовы к передаче\n"
        "• Полная безопасность сделки через проверенные площадки\n"
        "• Передача юзернейма каналом — быстро и надёжно\n\n"
    )
    if discount_active:
        welcome_text += (
            "🎁 <b>🔥 НЕДЕЛЯ СКИДОК!</b>\n"
            f"⏳ <b>Осталось:</b> {time_left}\n"
            "Скидка <b>25%</b> на ВСЕ юзернеймы! Цены уже пересчитаны.\n"
            "Успей выбрать свой идеальный ник! ⏳"
        )
    else:
        welcome_text += (
            "🌟 <b>Все цены актуальны.</b>\n"
            "Выбирай свой идеальный юзернейм прямо сейчас!"
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
    DISCOUNT = 25 if is_discount_active() else 0

    if data == "show_categories":
        time_left = get_time_left()
        discount_active = is_discount_active()
        keyboard = []
        for cat in products.keys():
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])
        header = f"📂 <b>Выбери категорию:</b>"
        if discount_active:
            header += f"\n\n⏳ <b>Осталось:</b> {time_left}\n🎁 Скидка <b>25%</b>!"
        else:
            header += "\n\n💰 Цены указаны без скидки."
        await query.edit_message_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("cat_"):
        category = data[4:]
        items = products.get(category, {})
        stats = load_stats()
        keyboard = []
        for prod_id, info in items.items():
            # Для категории NFT Аукционы показываем специальную кнопку
            if category == "NFT Аукционы":
                button_text = f"{info['name']} ⏳ Аукцион"
            else:
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
        found_category = None
        for cat, items in products.items():
            if prod_id in items:
                found = items[prod_id]
                found_category = cat
                break
        
        if not found:
            await query.edit_message_text("❌ Товар не найден.")
            return

        # ====== НОВАЯ ЛОГИКА ДЛЯ NFT АУКЦИОНОВ ======
        if found_category == "NFT Аукционы":
            # Парсим данные с Fragment
            username = found['name'].replace('@', '')
            auction_data = parse_fragment_auction(username)
            
            if auction_data:
                text = (
                    f"💎 <b>{found['name']}</b>\n\n"
                    f"📊 <b>Актуальные данные аукциона:</b>\n"
                    f"💰 Текущая ставка: <b>{auction_data['current_bid']} TON</b>\n"
                    f"👥 Количество ставок: {auction_data['bids_count']}\n"
                    f"📌 Статус: {auction_data['status']}\n\n"
                    f"🔗 <a href='{auction_data['url']}'>Перейти на Fragment</a>\n\n"
                    f"<i>Сделай ставку и получи этот юзернейм как NFT!</i>"
                )
            else:
                text = (
                    f"💎 <b>{found['name']}</b>\n\n"
                    f"⚠️ <b>Не удалось получить данные с Fragment</b>\n"
                    f"Попробуй обновить позже или перейди по ссылке:\n"
                    f"🔗 <a href='{found['fragment_url']}'>Открыть аукцион</a>"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔗 Открыть аукцион", url=found.get("fragment_url", ""))],
                [InlineKeyboardButton("🔄 Обновить данные", callback_data=f"prod_{prod_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="show_categories")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            return

        # ====== ОБЫЧНАЯ ЛОГИКА ДЛЯ ОСТАЛЬНЫХ КАТЕГОРИЙ ======
        views = increment_views(prod_id)
        discounted_price = apply_discount(found['price'], DISCOUNT)
        text = (
            f"💎 <b>{found['name']}</b>\n\n"
            f"💰 <b>Цена:</b>\n{discounted_price}\n\n"
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
    init_stats()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
