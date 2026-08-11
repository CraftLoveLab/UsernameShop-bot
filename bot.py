import logging
import json
import os
import re
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from stats_storage import increment_views, init_stats, load_stats

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
CONTACT_USERNAME = os.environ.get("CONTACT_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # если не задан, то дефолтный (НО ЛУЧШЕ ЗАДАТЬ В ПЕРЕМЕННЫХ!)

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

# Логирование админ-действий
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

# Получить следующий ID для категории
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

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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

# ================================================================
# ========== АДМИН-ПАНЕЛЬ (ЗАЩИТА ПАРОЛЕМ + ЛОГИ) ==========
# ================================================================

# Состояния для ConversationHandler
(PASSWORD, ADMIN_MENU, ADD_CATEGORY, ADD_ID, ADD_NAME, ADD_PRICE, ADD_GG, ADD_PLAYEROK, ADD_STARVELL, REMOVE_ID, EDIT_ID, EDIT_NEW_PRICE) = range(12)

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашиваем пароль для входа в админку"""
    await update.message.reply_text("🔐 Введите пароль для входа в админ-панель:\n(или /cancel для отмены)")
    return PASSWORD

async def admin_check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка пароля"""
    password = update.message.text
    if password == ADMIN_PASSWORD:
        context.user_data['admin_authenticated'] = True
        await show_admin_menu(update, context)
        return ADMIN_MENU
    else:
        await update.message.reply_text("❌ Неверный пароль. Попробуйте снова /admin")
        return ConversationHandler.END

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню админки (через редактирование или новое сообщение)"""
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

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок в админ-меню"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    username = user.username or user.first_name

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
            "Введите ID для нового товара (например, user45, garant13, crypto23):\n"
            "или /cancel для отмены",
            parse_mode="HTML"
        )
        context.user_data['admin_action'] = 'add_wait_id'
        context.user_data['admin_step'] = 'add_id'
        return

    if data == "admin_remove":
        # покажем список товаров для выбора
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
        # покажем список товаров для выбора цены
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
        await query.edit_message_text(
            f"Введите новую цену для товара (в формате 'X ₽ / Y TON', например '1500 ₽ / 13 TON'):\n"
            "или /cancel для отмены"
        )
        context.user_data['admin_action'] = 'edit_wait_price'
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
        last_10 = logs[-10:][::-1]  # последние 10
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
        context.user_data.pop('admin_action', None)
        context.user_data.pop('admin_step', None)
        await query.edit_message_text("🔒 Админ-панель закрыта.")
        return

# Обработка текстовых сообщений в процессе добавления/редактирования
async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    username = user.username or user.first_name

    if not context.user_data.get('admin_authenticated'):
        await update.message.reply_text("⛔ Доступ запрещён. Введите /admin")
        return

    action = context.user_data.get('admin_action')

    # Добавление товара — шаг ввода ID
    if action == 'add_wait_id':
        pid = text.strip()
        # проверка на уникальность
        products = load_products()
        for cat, items in products.items():
            if pid in items:
                await update.message.reply_text("❌ Товар с таким ID уже существует. Введите другой ID или /cancel")
                return
        context.user_data['admin_new_id'] = pid
        await update.message.reply_text("Введите название товара (например, @Test):")
        context.user_data['admin_action'] = 'add_wait_name'
        context.user_data['admin_step'] = 'add_name'
        return

    if action == 'add_wait_name':
        name = text.strip()
        context.user_data['admin_new_name'] = name
        await update.message.reply_text("Введите цену (например, '1000 ₽ / 8 TON'):")
        context.user_data['admin_action'] = 'add_wait_price'
        context.user_data['admin_step'] = 'add_price'
        return

    if action == 'add_wait_price':
        price = text.strip()
        # простая проверка формата (можно доработать)
        context.user_data['admin_new_price'] = price
        await update.message.reply_text("Введите ссылку GGSEL (или '-' если нет):")
        context.user_data['admin_action'] = 'add_wait_gg'
        context.user_data['admin_step'] = 'add_gg'
        return

    if action == 'add_wait_gg':
        gg = text.strip()
        if gg == '-':
            gg = ""
        context.user_data['admin_new_gg'] = gg
        await update.message.reply_text("Введите ссылку PLAYEROK (или '-' если нет):")
        context.user_data['admin_action'] = 'add_wait_playerok'
        context.user_data['admin_step'] = 'add_playerok'
        return

    if action == 'add_wait_playerok':
        playerok = text.strip()
        if playerok == '-':
            playerok = ""
        context.user_data['admin_new_playerok'] = playerok
        await update.message.reply_text("Введите ссылку STARVELL (или '-' если нет):")
        context.user_data['admin_action'] = 'add_wait_starvell'
        context.user_data['admin_step'] = 'add_starvell'
        return

    if action == 'add_wait_starvell':
        starvell = text.strip()
        if starvell == '-':
            starvell = ""

        # Собираем товар
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

        # очищаем временные данные
        for key in ['admin_add_category', 'admin_new_id', 'admin_new_name', 'admin_new_price', 'admin_new_gg', 'admin_new_playerok', 'admin_new_starvell']:
            context.user_data.pop(key, None)
        context.user_data.pop('admin_action', None)
        context.user_data.pop('admin_step', None)

        await update.message.reply_text(f"✅ Товар {name} добавлен в категорию {category}!")
        await show_admin_menu(update, context)
        return

    # Редактирование цены
    if action == 'edit_wait_price':
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
        context.user_data.pop('admin_action', None)
        context.user_data.pop('admin_edit_id', None)
        await show_admin_menu(update, context)
        return

# Отмена операции
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ Операция отменена.")

def main():
    init_stats()
    application = Application.builder().token(BOT_TOKEN).build()

    # Основные хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_start))

    # ConversationHandler для админ-входа по паролю
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)],
            ADMIN_MENU: [CallbackQueryHandler(admin_callback_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(conv_handler)

    # Обработчики кнопок (для меню и действий)
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^add_cat_"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^del_"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^edit_"))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Обработчик текста для админ-шагов (добавление, редактирование)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))

    # Остальные хендлеры
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
