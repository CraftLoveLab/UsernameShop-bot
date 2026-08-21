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
    print("❌ Ошибка: не заданы переменные окружения")
    exit(1)

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
# =================================

# ========== РАБОТА С ЯЗЫКОМ ==========
def get_user_lang(user_id):
    try:
        with open("user_lang.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id))
    except:
        return None

def set_user_lang(user_id, lang):
    try:
        with open("user_lang.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    data[str(user_id)] = lang
    with open("user_lang.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== ПЕРЕВОДЫ ==========
TEXTS = {
    'ru': {
        'lang_select': "🌐 Выберите язык / Choose language / اختر اللغة / 言語を選択してください:",
        'welcome': "✨ <b>Привет, {user}!</b> ✨\n\nДобро пожаловать в <b>TgUserStore</b> — твой личный каталог премиальных юзернеймов для Telegram.\n\n❓ <b>Почему юзернейм — это важно?</b>\nЮзернейм — это твой цифровой паспорт. Это первое, что видят люди, когда ты пишешь им. Это твой бренд, твоя визитка, твоё лицо в мире Telegram.\n\n🔥 <b>Примеры из жизни:</b>\n• Юзернейм @danbao продали за <b>$2,1–$2,2 млн / 1 583 948 TON</b>\n• @bank — за <b>~$1.34 млн / 850,000 TON</b>\n• Короткие имена — это статус, который работает на тебя 24/7\n\n💎 <b>Почему стоит купить у нас?</b>\n• Более 80+ уникальных ников — от коротких до тематических\n• Все юзы проверены и готовы к передаче\n• Полная безопасность сделки через проверенные площадки\n• Передача юзернейма каналом — быстро и надёжно\n\n🎁 <b>🔥 НЕДЕЛЯ СКИДОК!</b>\n⏳ <b>Осталось:</b> {time_left}\nСкидка <b>25%</b> на ВСЕ юзернеймы!\nУспей выбрать свой идеальный ник! ⏳",
        'no_discount': "🌟 <b>Все цены актуальны.</b>\nВыбирай свой идеальный юзернейм прямо сейчас!",
        'choose_category': "📂 <b>Выбери категорию:</b>",
        'category_items': "📦 <b>Товары в категории «{category}»:</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>Цена:</b>\n{price}\n\n👁️ <b>Просмотров:</b> {views}\n\n<i>Выбери способ покупки:</i>",
        'why_price': "❓ <b>Почему такая цена, если он не NFT?</b>\n\nВсе просто. Юзернейм — это не просто набор букв, а готовый цифровой актив. Даже если он не оформлен как NFT на Fragment, он обладает реальной рыночной ценностью, потому что:\n\n1. <b>Короткие имена всегда в дефиците</b> — их нельзя создать, их можно только перекупить у текущего владельца.\n\n2. <b>Осмысленные названия</b> — это готовые бренды для бизнеса, крипто-проектов, каналов и личного продвижения.\n\n3. <b>Рыночная цена формируется из спроса</b> на такие ники, а не из способа передачи. На Fragment за подобные имена платят тысячи долларов.\n\n4. <b>Возможности дальнейшей монетизации</b> — после покупки вы можете самостоятельно оформить этот юзернейм как NFT на Fragment.",
        'back_btn': "🔙 Назад",
        'shop_btn': "🛒 ПРИСТУПИТЬ К ПОКУПКАМ",
        'channel_btn': "📢 Наш канал",
        'contact_btn': "💬 Договориться лично",
        'spam_btn': "🚫 У меня спам-блок",
        'why_btn': "❓ Почему такая цена?",
        'currency': "₽"
    },
    'en': {
        'lang_select': "🌐 Select language / Choose language / اختر اللغة / 言語を選択してください:",
        'welcome': "✨ <b>Hello, {user}!</b> ✨\n\nWelcome to <b>TgUserStore</b> — your personal catalog of premium Telegram usernames.\n\n❓ <b>Why is a username important?</b>\nA username is your digital passport. It's the first thing people see when you message them.\n\n🔥 <b>Real examples:</b>\n• @danbao sold for <b>$2.1-2.2 million / 1,583,948 TON</b>\n• @bank — for <b>~$1.34 million / 850,000 TON</b>\n\n💎 <b>Why buy from us?</b>\n• 80+ unique nicknames\n• All usernames are verified\n• Full transaction security\n• Fast and reliable channel transfer\n\n🎁 <b>🔥 WEEK OF DISCOUNTS!</b>\n⏳ <b>Time left:</b> {time_left}\n<b>25%</b> discount on ALL usernames!",
        'no_discount': "🌟 <b>All prices are current.</b>\nChoose your perfect username right now!",
        'choose_category': "📂 <b>Choose a category:</b>",
        'category_items': "📦 <b>Items in category «{category}»:</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>Price:</b>\n{price}\n\n👁️ <b>Views:</b> {views}\n\n<i>Choose purchase method:</i>",
        'why_price': "❓ <b>Why this price if it's not NFT?</b>\n\nSimple. A username is not just a set of letters, but a ready-made digital asset. Even if it's not minted as NFT on Fragment, it has real market value because:\n\n1. <b>Short names are always in short supply</b>\n2. <b>Meaningful names</b> are ready-made brands\n3. <b>Market price is driven by demand</b>\n4. <b>Future monetization opportunity</b> — you can mint it as NFT on Fragment.",
        'back_btn': "🔙 Back",
        'shop_btn': "🛒 START SHOPPING",
        'channel_btn': "📢 Our channel",
        'contact_btn': "💬 Contact me",
        'spam_btn': "🚫 I have spam-block",
        'why_btn': "❓ Why this price?",
        'currency': "$"
    },
    'ar': {
        'lang_select': "🌐 اختر اللغة / Choose language / Select language / 言語を選択してください:",
        'welcome': "✨ <b>مرحبًا، {user}!</b> ✨\n\nمرحبًا بك في <b>TgUserStore</b> — كتالوجك الشخصي لأسماء المستخدمين المميزة في تيليجرام.\n\n🎁 <b>🔥 أسبوع التخفيضات!</b>\n⏳ <b>الوقت المتبقي:</b> {time_left}\nخصم <b>25%</b> على جميع الأسماء!",
        'no_discount': "🌟 <b>جميع الأسعار محدثة.</b>\nاختر اسم المستخدم المثالي الآن!",
        'choose_category': "📂 <b>اختر الفئة:</b>",
        'category_items': "📦 <b>العناصر في فئة «{category}»:</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>السعر:</b>\n{price}\n\n👁️ <b>المشاهدات:</b> {views}\n\n<i>اختر طريقة الشراء:</i>\n\n⚠️ <b>ملاحظة:</b> إذا كنت تدفع بالدولار، استخدم GGSEL.",
        'why_price': "❓ <b>لماذا هذا السعر إذا كان ليس NFT؟</b>\n\nببساطة. اسم المستخدم ليس مجرد مجموعة حروف، بل أصل رقمي جاهز...",
        'back_btn': "🔙 العودة",
        'shop_btn': "🛒 ابدأ التسوق",
        'channel_btn': "📢 قناتنا",
        'contact_btn': "💬 تفاوض شخصيًا",
        'spam_btn': "🚫 لدي حظر للرسائل",
        'why_btn': "❓ لماذا هذا السعر؟",
        'currency': "$"
    },
    'ja': {
        'lang_select': "🌐 言語を選択 / Choose language / اختر اللغة / Select language:",
        'welcome': "✨ <b>こんにちは、{user}！</b> ✨\n\n<b>TgUserStore</b>へようこそ — Telegramのプレミアムユーザーネームの個人カタログです。\n\n🎁 <b>🔥 割引ウィーク！</b>\n⏳ <b>残り時間：</b> {time_left}\nすべてのユーザーネームが <b>25%</b> オフ！",
        'no_discount': "🌟 <b>すべての価格は最新です。</b>\n今すぐ完璧なユーザーネームを選びましょう！",
        'choose_category': "📂 <b>カテゴリを選択してください：</b>",
        'category_items': "📦 <b>カテゴリ「{category}」のアイテム：</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>価格：</b>\n{price}\n\n👁️ <b>閲覧数：</b> {views}\n\n<i>購入方法を選択してください：</i>",
        'why_price': "❓ <b>NFTでないのにこの価格なのはなぜ？</b>\n\n簡単です。ユーザーネームは単なる文字列ではなく、既製のデジタル資産です...",
        'back_btn': "🔙 戻る",
        'shop_btn': "🛒 ショッピングを始める",
        'channel_btn': "📢 チャンネル",
        'contact_btn': "💬 直接交渉",
        'spam_btn': "🚫 スパムブロックあり",
        'why_btn': "❓ なぜこの価格？",
        'currency': "$"
    }
}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def load_products():
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def get_time_left(lang='ru'):
    end_date = datetime(2026, 8, 14, 6, 0, 0)
    now = datetime.now()
    if now >= end_date:
        return "❌ Акция завершена!" if lang == 'ru' else "❌ Discount ended!"
    diff = end_date - now
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(f"{days} дн" if lang == 'ru' else f"{days} d")
    if hours > 0:
        parts.append(f"{hours} ч" if lang == 'ru' else f"{hours} h")
    if minutes > 0:
        parts.append(f"{minutes} мин" if lang == 'ru' else f"{minutes} m")
    return " ".join(parts) if parts else ("менее минуты" if lang == 'ru' else "less than a minute")

def is_discount_active():
    return datetime.now() < datetime(2026, 8, 14, 6, 0, 0)

def apply_discount(price_text):
    if not is_discount_active():
        return price_text
    pattern = r'([\d\s]+)\s*(₽|TON)'
    matches = re.findall(pattern, price_text)
    if not matches:
        return price_text
    result = []
    for num_str, currency in matches:
        clean = int(num_str.replace(' ', ''))
        discounted = clean * 75 // 100
        formatted = f"{discounted:,}".replace(',', ' ')
        result.append(f"{formatted} {currency}")
    return ' / '.join(result) if result else price_text

def format_price(rub_price, lang, ton_price=''):
    if lang == 'ru':
        return f"{rub_price} / {ton_price}" if ton_price else rub_price
    else:
        clean = rub_price.replace(' ', '').replace('₽', '').strip()
        try:
            rub_num = int(clean)
        except:
            rub_num = 0
        usd = round(rub_num / 90, 2)
        return f"${usd} / {ton_price}" if ton_price else f"${usd}"

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if not lang:
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("🇯🇵 日本語", callback_data="lang_ja")],
        ]
        await update.message.reply_text(TEXTS['ru']['lang_select'], reply_markup=InlineKeyboardMarkup(keyboard))
        return
    await show_welcome(update, context, lang)

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    user_id = update.effective_user.id
    set_user_lang(user_id, lang)
    await show_welcome(update, context, lang)

async def show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, lang):
    user = update.effective_user
    t = TEXTS[lang]
    time_left = get_time_left(lang)
    if is_discount_active():
        text = t['welcome'].format(user=user.first_name, time_left=time_left)
    else:
        text = t['welcome'].format(user=user.first_name, time_left="")
        text += "\n\n" + t['no_discount']
    keyboard = [
        [InlineKeyboardButton(t['shop_btn'], callback_data="shop")],
        [InlineKeyboardButton(t['channel_btn'], url="https://t.me/EliteTGUsername")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id) or 'ru'
    t = TEXTS[lang]
    products = load_products()

    if data == "why":
        await query.edit_message_text(t['why_price'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t['back_btn'], callback_data="shop")]]), parse_mode="HTML")
        return

    if data == "shop":
        keyboard = []
        for cat in products.keys():
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        keyboard.append([InlineKeyboardButton(t['why_btn'], callback_data="why")])
        await query.edit_message_text(t['choose_category'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data.startswith("cat_"):
        category = data[4:]
        items = products.get(category, {})
        keyboard = []
        for pid, info in items.items():
            price = format_price(info['price'].split(' / ')[0], lang, info['price'].split(' / ')[1] if ' / ' in info['price'] else '')
            keyboard.append([InlineKeyboardButton(f"{info['name']} — {price}", callback_data=f"prod_{pid}")])
        keyboard.append([InlineKeyboardButton(t['back_btn'], callback_data="shop")])
        await query.edit_message_text(t['category_items'].format(category=category), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data.startswith("prod_"):
        pid = data[5:]
        found = None
        for cat, items in products.items():
            if pid in items:
                found = items[pid]
                break
        if found:
            price = format_price(found['price'].split(' / ')[0], lang, found['price'].split(' / ')[1] if ' / ' in found['price'] else '')
            text = t['product_card'].format(name=found['name'], price=price, views=0)
            keyboard = [
                [InlineKeyboardButton("🔗 GGSEL", url=found.get("link_ggsel", ""))],
                [InlineKeyboardButton("🔗 PLAYEROK", url=found.get("link_playerok", ""))],
                [InlineKeyboardButton("🔗 STARVELL", url=found.get("link_starvell", ""))],
                [InlineKeyboardButton(t['contact_btn'], callback_data=f"contact_{pid}")],
                [InlineKeyboardButton(t['why_btn'], callback_data="why")],
                [InlineKeyboardButton(t['back_btn'], callback_data="shop")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data.startswith("contact_"):
        await query.edit_message_text(f"💬 {t['contact_btn']}: @{CONTACT_USERNAME}\n\nМы ответим.", parse_mode="HTML")
        return

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Отменено.")

# ========== ЗАПУСК ==========
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))

    print("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
