import logging
import json
import os
import re
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from stats_storage import increment_views, init_stats, load_stats

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
CONTACT_USERNAME = os.environ.get("CONTACT_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

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

def save_products(products):
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def log_admin_action(action, details, username="Неизвестный"):
    try:
        with open("admin_log.json", "r", encoding="utf-8") as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []
    logs.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "user": username,
        "details": details
    })
    with open("admin_log.json", "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def get_next_id(category):
    prefix_map = {
        "Обычные": "user",
        "Гаранты": "garant",
        "Крипта / NFT": "crypto"
    }
    prefix = prefix_map.get(category, "item")
    existing_ids = [k for k in load_products().get(category, {}).keys() if k.startswith(prefix)]
    if not existing_ids:
        return f"{prefix}1"
    numbers = [int(re.search(r'\d+', id).group()) for id in existing_ids if re.search(r'\d+', id)]
    next_num = max(numbers) + 1 if numbers else 1
    return f"{prefix}{next_num}"

# Проверка, активна ли скидка
def is_discount_active():
    end_date = datetime(2026, 8, 14, 6, 0, 0)
    return datetime.now() < end_date

# Применяем скидку (только если активна)
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

# Таймер (или сообщение о завершении)
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

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    discount_active = is_discount_active()
    time_left = get_time_left()

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
        "• Более 60+ уникальных ников — от коротких до тематических\n"
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

    # --- Кнопка "Почему такая цена?" ---
    if data == "why_price":
        text = (
            "❓ <b>Почему такая цена, если он не NFT?</b>\n\n"
            "Все просто. Юзернейм — это не просто набор букв, а готовый цифровой актив. "
            "Даже если он не оформлен как NFT на Fragment, он обладает реальной рыночной ценностью, потому что:\n\n"
            "1. <b>Короткие имена всегда в дефиците</b> — их нельзя создать, их можно только перекупить у текущего владельца.\n\n"
            "2. <b>Осмысленные названия</b> (TraderTitle, sellerSOL, DHSMarket) — это готовые бренды для бизнеса, крипто-проектов, каналов и личного продвижения.\n\n"
            "3. <b>Рыночная цена формируется из спроса</b> на такие ники, а не из способа передачи. На Fragment за подобные имена платят тысячи долларов (например, @bank, @auto). Моя цена — это рыночный ориентир, а не «цена за NFT».\n\n"
            "4. <b>Возможности дальнейшей монетизации</b> — после покупки вы можете самостоятельно оформить этот юзернейм как NFT на Fragment (при наличии 18+ возраста и кошелька TON)."
        )
        keyboard = [[InlineKeyboardButton("🔙 Назад к категориям", callback_data="show_categories")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data == "show_categories":
        time_left = get_time_left()
        discount_active = is_discount_active()
        keyboard = []
        for cat in products.keys():
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        # Добавляем кнопку с вопросом (без кнопки "Назад")
        keyboard.append([InlineKeyboardButton("❓ Почему такая цена?", callback_data="why_price")])
        header = f"📂 <b>Выбери категорию:</b>"
        if discount_active:
            header += f"\n\n⏳ <b>Осталось:</b> {time_left}\n🎁 Скидка <b>25%</b>!"
        else:
            header += "\n\n💰 Цены указаны без скидки."
        await query.edit_message_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

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
        return

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
                f"💰 <b>Цена:</b>\n{discounted_price}\n\n"
                f"👁️ <b>Просмотров:</b> {views}\n\n"
                f"<i>Выбери способ покупки:</i>"
            )
            keyboard = [
                [InlineKeyboardButton("🔗 GGSEL", url=found.get("link_ggsel", ""))],
                [InlineKeyboardButton("🔗 PLAYEROK", url=found.get("link_playerok", ""))],
                [InlineKeyboardButton("🔗 STARVELL", url=found.get("link_starvell", ""))],
                [InlineKeyboardButton("💬 Договориться лично", callback_data=f"contact_{prod_id}")],
                [InlineKeyboardButton("❓ Почему такая цена?", callback_data="why_price")],
                [InlineKeyboardButton("🔙 Назад", callback_data="show_categories")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Товар не найден.")
        return

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
        return

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
        return

    elif data == "back_to_start":
        await start(update, context)
        return

# ================================================================
# ========== АДМИН-ПАНЕЛЬ (упрощённая, без ConversationHandler) =
# ================================================================

admin_steps = {}

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашиваем пароль для входа в админку"""
    await update.message.reply_text("🔐 Введите пароль для входа в админ-панель:")
    context.user_data['admin_waiting_password'] = True

async def admin_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений для админ-панели"""
    user_id = update.effective_user.id
    text = update.message.text
    username = update.effective_user.username or update.effective_user.first_name

    # Если мы ждём пароль
    if context.user_data.get('admin_waiting_password'):
        if text == ADMIN_PASSWORD:
            context.user_data['admin_waiting_password'] = False
            context.user_data['admin_authenticated'] = True
            await show_admin_menu(update, context)
        else:
            await update.message.reply_text("❌ Неверный пароль. Попробуйте /admin")
        return

    # Если не авторизован — выходим
    if not context.user_data.get('admin_authenticated'):
        await update.message.reply_text("⛔ Доступ запрещён. Введите /admin")
        return

    # Обработка пошаговых действий
    step = context.user_data.get('admin_step')

    if step == 'add_wait_id':
        pid = text.strip()
        products = load_products()
        for cat, items in products.items():
            if pid in items:
                await update.message.reply_text("❌ Товар с таким ID уже существует. Введите другой ID или /cancel")
                return
        context.user_data['admin_new_id'] = pid
        context.user_data['admin_step'] = 'add_wait_name'
        await update.message.reply_text("Введите название товара (например, @Test):")
        return

    if step == 'add_wait_name':
        name = text.strip()
        context.user_data['admin_new_name'] = name
        context.user_data['admin_step'] = 'add_wait_price'
        await update.message.reply_text("Введите цену (например, '1000 ₽ / 8 TON'):")
        return

    if step == 'add_wait_price':
        price = text.strip()
        context.user_data['admin_new_price'] = price
        context.user_data['admin_step'] = 'add_wait_gg'
        await update.message.reply_text("Введите ссылку GGSEL (или '-' если нет):")
        return

    if step == 'add_wait_gg':
        gg = text.strip()
        if gg == '-':
            gg = ""
        context.user_data['admin_new_gg'] = gg
        context.user_data['admin_step'] = 'add_wait_playerok'
        await update.message.reply_text("Введите ссылку PLAYEROK (или '-' если нет):")
        return

    if step == 'add_wait_playerok':
        playerok = text.strip()
        if playerok == '-':
            playerok = ""
        context.user_data['admin_new_playerok'] = playerok
        context.user_data['admin_step'] = 'add_wait_starvell'
        await update.message.reply_text("Введите ссылку STARVELL (или '-' если нет):")
        return

    if step == 'add_wait_starvell':
        starvell = text.strip()
        if starvell == '-':
            starvell = ""

        category = context.user_data.get('admin_add_category')
        pid = context.user_data.get('admin_new_id')
        name = context.user_data.get('admin_new_name')
        price = context.user_data.get('admin_new_price')
        gg = context.user_data.get('admin_new_gg')
        playerok = context.user_data.get('admin_new_playerok')

        products = load_products()
        if category not in products:
            products[category] = {}
        products[category][pid] = {
            "name": name,
            "price": price,
            "link_ggsel": gg,
            "link_playerok": playerok,
            "link_starvell": starvell
        }
        save_products(products)
        log_admin_action("add", f"Добавлен товар {name} (ID: {pid}) в категорию {category}", username)

        context.user_data.pop('admin_step', None)
        context.user_data.pop('admin_add_category', None)
        context.user_data.pop('admin_new_id', None)
        context.user_data.pop('admin_new_name', None)
        context.user_data.pop('admin_new_price', None)
        context.user_data.pop('admin_new_gg', None)
        context.user_data.pop('admin_new_playerok', None)
        context.user_data.pop('admin_new_starvell', None)

        await update.message.reply_text(f"✅ Товар {name} добавлен в категорию {category}!")
        await show_admin_menu(update, context)
        return

    if step == 'edit_wait_price':
        pid = context.user_data.get('admin_edit_id')
        new_price = text.strip()
        products = load_products()
        found = False
        for cat, items in products.items():
            if pid in items:
                items[pid]['price'] = new_price
                found = True
                log_admin_action("edit", f"Изменена цена товара {items[pid]['name']} (ID: {pid}) на {new_price}", username)
                break
        if found:
            save_products(products)
            await update.message.reply_text(f"✅ Цена для {pid} обновлена на {new_price}")
        else:
            await update.message.reply_text("❌ Товар не найден.")
        context.user_data.pop('admin_step', None)
        context.user_data.pop('admin_edit_id', None)
        await show_admin_menu(update, context)
        return

    await update.message.reply_text("ℹ️ Используйте кнопки меню или /cancel")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок в админ-меню"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    if not context.user_data.get('admin_authenticated'):
        await query.edit_message_text("⛔ Доступ запрещён. Введите /admin")
        return

    if data == "admin_add":
        await query.edit_message_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📁 Обычные", callback_data="add_cat_Обычные")],
            [InlineKeyboardButton("🛡️ Гаранты", callback_data="add_cat_Гаранты")],
            [InlineKeyboardButton("💎 Крипта / NFT", callback_data="add_cat_Крипта / NFT")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]))
        return

    if data.startswith("add_cat_"):
        category = data[8:]
        context.user_data['admin_add_category'] = category
        next_id = get_next_id(category)
        await query.edit_message_text(
            f"Категория: <b>{category}</b>\n"
            f"Следующий ID: <code>{next_id}</code>\n\n"
            "Введите ID для нового товара (например, user45, garant13, crypto23):",
            parse_mode="HTML"
        )
        context.user_data['admin_step'] = 'add_wait_id'
        return

    if data == "admin_remove":
        products = load_products()
        keyboard = []
        for cat, items in products.items():
            for pid, info in items.items():
                keyboard.append([InlineKeyboardButton(f"Удалить {info['name']} ({pid})", callback_data=f"del_{pid}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        await query.edit_message_text("Выберите товар для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("del_"):
        pid = data[4:]
        products = load_products()
        found_cat = None
        found_item = None
        for cat, items in products.items():
            if pid in items:
                found_cat = cat
                found_item = items[pid]
                break
        if not found_item:
            await query.edit_message_text("❌ Товар не найден.")
            return
        name = found_item.get('name', pid)
        del products[found_cat][pid]
        save_products(products)
        log_admin_action("delete", f"Удалён товар {name} (ID: {pid}) из категории {found_cat}", username)
        await query.edit_message_text(f"✅ Товар {name} удалён.")
        await show_admin_menu(update, context)
        return

    if data == "admin_edit":
        products = load_products()
        keyboard = []
        for cat, items in products.items():
            for pid, info in items.items():
                keyboard.append([InlineKeyboardButton(f"{info['name']} ({pid})", callback_data=f"edit_{pid}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        await query.edit_message_text("Выберите товар для изменения цены:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("edit_"):
        pid = data[5:]
        context.user_data['admin_edit_id'] = pid
        context.user_data['admin_step'] = 'edit_wait_price'
        await query.edit_message_text(
            "Введите новую цену для товара (в формате 'X ₽ / Y TON', например '1500 ₽ / 13 TON'):"
        )
        return

    if data == "admin_stats":
        stats = load_stats()
        total_views = sum(stats.values())
        msg = f"📊 <b>Статистика просмотров</b>\n\nВсего просмотров: {total_views}\n\n"
        sorted_items = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]
        if sorted_items:
            for pid, views in sorted_items:
                name = pid
                for cat, items in load_products().items():
                    if pid in items:
                        name = items[pid].get('name', pid)
                        break
                msg += f"• {name}: {views} просмотров\n"
        else:
            msg += "Нет данных."
        await query.edit_message_text(msg, parse_mode="HTML")
        await show_admin_menu(update, context)
        return

    if data == "admin_logs":
        try:
            with open("admin_log.json", "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logs = []
        if not logs:
            await query.edit_message_text("📜 История действий пуста.")
            await show_admin_menu(update, context)
            return
        last_10 = logs[-10:][::-1]
        msg = "📜 <b>Последние действия:</b>\n\n"
        for log in last_10:
            msg += f"• {log['time']} — {log['user']}: {log['details']}\n"
        await query.edit_message_text(msg, parse_mode="HTML")
        await show_admin_menu(update, context)
        return

    if data == "admin_back":
        await show_admin_menu(update, context)
        return

    if data == "admin_close":
        context.user_data.pop('admin_authenticated', None)
        context.user_data.pop('admin_step', None)
        await query.edit_message_text("🔒 Админ-панель закрыта.")
        return

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню админки"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add")],
        [InlineKeyboardButton("➖ Удалить товар", callback_data="admin_remove")],
        [InlineKeyboardButton("✏️ Изменить цену", callback_data="admin_edit")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📜 История действий", callback_data="admin_logs")],
        [InlineKeyboardButton("❌ Закрыть админку", callback_data="admin_close")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🛠 <b>Админ-панель</b>\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "🛠 <b>Админ-панель</b>\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    context.user_data.clear()
    await update.message.reply_text("✅ Операция отменена.")

def main():
    init_stats()
    application = Application.builder().token(BOT_TOKEN).build()

    # Основные хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_start))
    application.add_handler(CommandHandler("cancel", cancel))

    # Обработчик текстовых сообщений (для пароля и шагов)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_text))

    # Админские кнопки (приоритет выше)
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(admin_|add_cat_|del_|edit_)"))

    # Основной обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
