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

# ========== РАБОТА С ЯЗЫКОМ (с созданием файла) ==========
LANG_FILE = "user_lang.json"

def _ensure_lang_file():
    """Создаёт файл user_lang.json, если его нет"""
    if not os.path.exists(LANG_FILE):
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        print("✅ Создан файл user_lang.json")

def get_user_lang(user_id):
    _ensure_lang_file()
    try:
        with open(LANG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id))
    except Exception as e:
        print(f"⚠️ Ошибка чтения user_lang.json: {e}")
        return None

def set_user_lang(user_id, lang):
    _ensure_lang_file()
    try:
        with open(LANG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    data[str(user_id)] = lang
    try:
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Язык для {user_id} сохранён: {lang}")
    except Exception as e:
        print(f"❌ Ошибка записи user_lang.json: {e}")

# ========== ПЕРЕВОДЫ ==========
TRANSLATIONS = {
    'ru': {
        'welcome': "✨ <b>Привет, {user}!</b> ✨\n\nДобро пожаловать в <b>TgUserStore</b> — твой личный каталог премиальных юзернеймов для Telegram.\n\n❓ <b>Почему юзернейм — это важно?</b>\nЮзернейм — это твой цифровой паспорт. Это первое, что видят люди, когда ты пишешь им. Это твой бренд, твоя визитка, твоё лицо в мире Telegram.\n\n🔥 <b>Примеры из жизни:</b>\n• Юзернейм @danbao продали за <b>$2,1–$2,2 млн / 1 583 948 TON</b>\n• @bank — за <b>~$1.34 млн / 850,000 TON</b>\n• Короткие имена — это статус, который работает на тебя 24/7\n\n💎 <b>Почему стоит купить у нас?</b>\n• Более 80+ уникальных ников — от коротких до тематических\n• Все юзы проверены и готовы к передаче\n• Полная безопасность сделки через проверенные площадки\n• Передача юзернейма каналом — быстро и надёжно\n\n🎁 <b>🔥 НЕДЕЛЯ СКИДОК!</b>\n⏳ <b>Осталось:</b> {time_left}\nСкидка <b>25%</b> на ВСЕ юзернеймы! Цены уже пересчитаны.\nУспей выбрать свой идеальный ник! ⏳",
        'choose_category': "📂 <b>Выбери категорию:</b>\n\n⏳ <b>Осталось:</b> {time_left}\n🎁 Скидка <b>25%</b>!",
        'no_discount': "🌟 <b>Все цены актуальны.</b>\nВыбирай свой идеальный юзернейм прямо сейчас!",
        'category_items': "📦 <b>Товары в категории «{category}»:</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>Цена:</b>\n{price}\n\n👁️ <b>Просмотров:</b> {views}\n\n<i>Выбери способ покупки:</i>",
        'contact_admin': "💬 <b>Свяжись с нами:</b> @{contact}\n\nМы ответим.\n\n🚫 Если спам-блок — нажми ниже.",
        'spam_block': "✅ <b>Понял!</b>\n\nМы свяжемся сами.",
        'why_price': "❓ <b>Почему такая цена, если он не NFT?</b>\n\nВсе просто. Юзернейм — это не просто набор букв, а готовый цифровой актив. Даже если он не оформлен как NFT на Fragment, он обладает реальной рыночной ценностью, потому что:\n\n1. <b>Короткие имена всегда в дефиците</b> — их нельзя создать, их можно только перекупить у текущего владельца.\n\n2. <b>Осмысленные названия</b> (TraderTitle, sellerSOL, DHSMarket) — это готовые бренды для бизнеса, крипто-проектов, каналов и личного продвижения.\n\n3. <b>Рыночная цена формируется из спроса</b> на такие ники, а не из способа передачи. На Fragment за подобные имена платят тысячи долларов (например, @bank, @auto). Моя цена — это рыночный ориентир, а не «цена за NFT».\n\n4. <b>Возможности дальнейшей монетизации</b> — после покупки вы можете самостоятельно оформить этот юзернейм как NFT на Fragment (при наличии 18+ возраста и кошелька TON).",
        'back_to_categories': "🔙 Назад к категориям",
        'why_price_btn': "❓ Почему такая цена?",
        'start_shopping_btn': "🛒 ПРИСТУПИТЬ К ПОКУПКАМ",
        'channel_btn': "📢 Наш канал с новинками",
        'contact_btn': "💬 Договориться лично",
        'spam_btn': "🚫 У меня спам-блок",
        'ar_warning': "",
        'currency': "₽",
        'select_lang': "🌐 Выберите язык / Choose language / اختر اللغة / 言語を選択してください:",
        'lang_selected': "✅ Язык сохранён! Теперь выберите действие.",
    },
    'en': {
        'welcome': "✨ <b>Hello, {user}!</b> ✨\n\nWelcome to <b>TgUserStore</b> — your personal catalog of premium Telegram usernames.\n\n❓ <b>Why is a username important?</b>\nA username is your digital passport. It's the first thing people see when you message them. It's your brand, your business card, your face in the Telegram world.\n\n🔥 <b>Real-life examples:</b>\n• Username @danbao sold for <b>$2.1–$2.2 million / 1,583,948 TON</b>\n• @bank — for <b>~$1.34 million / 850,000 TON</b>\n• Short names are status that works for you 24/7\n\n💎 <b>Why buy from us?</b>\n• 80+ unique nicknames — from short to niche\n• All usernames are verified and ready for transfer\n• Full transaction security through trusted platforms\n• Channel-based transfer — fast and reliable\n\n🎁 <b>🔥 WEEK OF DISCOUNTS!</b>\n⏳ <b>Time left:</b> {time_left}\n<b>25%</b> discount on ALL usernames! Prices already recalculated.\nHurry up and choose your ideal nickname! ⏳",
        'choose_category': "📂 <b>Choose a category:</b>\n\n⏳ <b>Time left:</b> {time_left}\n🎁 <b>25%</b> discount!",
        'no_discount': "🌟 <b>All prices are current.</b>\nChoose your perfect username right now!",
        'category_items': "📦 <b>Items in category «{category}»:</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>Price:</b>\n{price}\n\n👁️ <b>Views:</b> {views}\n\n<i>Choose purchase method:</i>",
        'contact_admin': "💬 <b>Contact us:</b> @{contact}\n\nWe will respond.\n\n🚫 If you have spam-block — press below.",
        'spam_block': "✅ <b>Got it!</b>\n\nWe will contact you.",
        'why_price': "❓ <b>Why this price if it's not NFT?</b>\n\nSimple. A username is not just a set of letters, but a ready-made digital asset. Even if it's not minted as NFT on Fragment, it has real market value because:\n\n1. <b>Short names are always in short supply</b> — they cannot be created, only bought from the current owner.\n\n2. <b>Meaningful names</b> (TraderTitle, sellerSOL, DHSMarket) — are ready-made brands for business, crypto projects, channels, and personal branding.\n\n3. <b>Market price is driven by demand</b> for such nicknames, not by the transfer method. On Fragment, similar names sell for thousands of dollars (e.g., @bank, @auto). My price is a market benchmark, not an «NFT price».\n\n4. <b>Future monetization opportunity</b> — after purchase, you can mint this username as NFT on Fragment (if you are 18+ and have a TON wallet).",
        'back_to_categories': "🔙 Back to categories",
        'why_price_btn': "❓ Why this price?",
        'start_shopping_btn': "🛒 START SHOPPING",
        'channel_btn': "📢 Our channel with new items",
        'contact_btn': "💬 Negotiate personally",
        'spam_btn': "🚫 I have spam-block",
        'ar_warning': "",
        'currency': "$",
        'select_lang': "🌐 Select language / Choose language / اختر اللغة / 言語を選択してください:",
        'lang_selected': "✅ Language saved! Now choose an action.",
    },
    'ar': {
        # ... (оставляю как в предыдущем коде, но сокращу для экономии места)
        'welcome': "✨ <b>مرحبًا، {user}!</b> ✨\n\nمرحبًا بك في <b>TgUserStore</b> — كتالوجك الشخصي لأسماء المستخدمين المميزة في تيليجرام.\n\n❓ <b>لماذا اسم المستخدم مهم؟</b>\nاسم المستخدم هو جواز سفرك الرقمي. إنه أول شيء يراه الناس عندما تراسلهم. إنه علامتك التجارية، بطاقة عملك، وجهك في عالم تيليجرام.\n\n🔥 <b>أمثلة من الواقع:</b>\n• اسم المستخدم @danbao بيع بـ <b>$2.1–$2.2 مليون / 1,583,948 TON</b>\n• @bank — بـ <b>~$1.34 مليون / 850,000 TON</b>\n• الأسماء القصيرة هي مكانة تعمل لصالحك 24/7\n\n💎 <b>لماذا تشتري منا؟</b>\n• أكثر من 80+ اسمًا فريدًا — من القصير إلى المتخصص\n• جميع الأسماء موثقة وجاهزة للنقل\n• أمان تام للصفقة عبر منصات موثوقة\n• النقل عبر القناة — سريع وموثوق\n\n🎁 <b>🔥 أسبوع التخفيضات!</b>\n⏳ <b>الوقت المتبقي:</b> {time_left}\nخصم <b>25%</b> على جميع الأسماء! الأسعار محسوبة بالفعل.\nأسرع واختر اسمك المثالي! ⏳",
        'choose_category': "📂 <b>اختر الفئة:</b>\n\n⏳ <b>الوقت المتبقي:</b> {time_left}\n🎁 خصم <b>25%</b>!",
        'no_discount': "🌟 <b>جميع الأسعار محدثة.</b>\nاختر اسم المستخدم المثالي الآن!",
        'category_items': "📦 <b>العناصر في فئة «{category}»:</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>السعر:</b>\n{price}\n\n👁️ <b>المشاهدات:</b> {views}\n\n<i>اختر طريقة الشراء:</i>\n\n⚠️ <b>ملاحظة:</b> إذا كنت تدفع بالدولار، استخدم GGSEL (الزر الأول).",
        'contact_admin': "💬 <b>اتصل بنا:</b> @{contact}\n\nسوف نرد.\n\n🚫 إذا كان لديك حظر للرسائل — اضغط أدناه.",
        'spam_block': "✅ <b>فهمت!</b>\n\nسوف نتصل بك.",
        'why_price': "❓ <b>لماذا هذا السعر إذا كان ليس NFT؟</b>\n\nببساطة. اسم المستخدم ليس مجرد مجموعة حروف، بل أصل رقمي جاهز. حتى لو لم يتم سكه كـ NFT على Fragment، فإن له قيمة سوقية حقيقية لأن:\n\n1. <b>الأسماء القصيرة دائمًا نادرة</b> — لا يمكن إنشاؤها، بل شراؤها من المالك الحالي فقط.\n\n2. <b>الأسماء ذات المعنى</b> (TraderTitle, sellerSOL, DHSMarket) — هي علامات تجارية جاهزة للأعمال، المشاريع المشفرة، القنوات، والتسويق الشخصي.\n\n3. <b>السعر السوقي يتحدد حسب الطلب</b> على هذه الأسماء، وليس حسب طريقة النقل. على Fragment، تباع أسماء مشابهة بآلاف الدولارات (مثل @bank، @auto). سعري هو معيار سوقي، وليس «سعر NFT».\n\n4. <b>فرصة تحقيق الربح مستقبلًا</b> — بعد الشراء، يمكنك سك هذا الاسم كـ NFT على Fragment (إذا كنت فوق 18 عامًا ولديك محفظة TON).",
        'back_to_categories': "🔙 العودة إلى الفئات",
        'why_price_btn': "❓ لماذا هذا السعر؟",
        'start_shopping_btn': "🛒 ابدأ التسوق",
        'channel_btn': "📢 قناتنا مع الجديد",
        'contact_btn': "💬 تفاوض شخصيًا",
        'spam_btn': "🚫 لدي حظر للرسائل",
        'ar_warning': "\n\n⚠️ <b>تنبيه:</b> إذا كنت تدفع بالدولار، استخدم GGSEL (الزر الأول).",
        'currency': "$",
        'select_lang': "🌐 اختر اللغة / Choose language / Select language / 言語を選択してください:",
        'lang_selected': "✅ تم حفظ اللغة! اختر الآن إجراءً.",
    },
    'ja': {
        # ... кратко, чтобы не занимать место
        'welcome': "✨ <b>こんにちは、{user}！</b> ✨\n\n<b>TgUserStore</b>へようこそ — Telegramのプレミアムユーザーネームの個人カタログです。\n\n❓ <b>ユーザーネームが重要な理由は？</b>\nユーザーネームはあなたのデジタルパスポートです。メッセージを送る際に最初に目に入るものです。それはあなたのブランド、名刺、Telegramの世界での顔です。\n\n🔥 <b>実際の例：</b>\n• @danbao は <b>$2.1–$2.2 百万 / 1,583,948 TON</b> で販売\n• @bank — <b>~$1.34 百万 / 850,000 TON</b>\n• 短い名前は24時間あなたのために働くステータスです\n\n💎 <b>なぜ私たちから買うべきか？</b>\n• 80+ のユニークなニックネーム — 短いものからニッチなものまで\n• すべてのユーザーネームは検証済みで譲渡準備完了\n• 信頼できるプラットフォームを通じた取引の完全なセキュリティ\n• チャンネルベースの譲渡 — 迅速で信頼性が高い\n\n🎁 <b>🔥 割引ウィーク！</b>\n⏳ <b>残り時間：</b> {time_left}\nすべてのユーザーネームが <b>25%</b> オフ！価格は再計算済み。\n理想のニックネームを今すぐ選びましょう！ ⏳",
        'choose_category': "📂 <b>カテゴリを選択してください：</b>\n\n⏳ <b>残り時間：</b> {time_left}\n🎁 <b>25%</b> 割引！",
        'no_discount': "🌟 <b>すべての価格は最新です。</b>\n今すぐ完璧なユーザーネームを選びましょう！",
        'category_items': "📦 <b>カテゴリ「{category}」のアイテム：</b>",
        'product_card': "💎 <b>{name}</b>\n\n💰 <b>価格：</b>\n{price}\n\n👁️ <b>閲覧数：</b> {views}\n\n<i>購入方法を選択してください：</i>",
        'contact_admin': "💬 <b>お問い合わせ：</b> @{contact}\n\n返信いたします。\n\n🚫 スパムブロックがある場合は下を押してください。",
        'spam_block': "✅ <b>了解しました！</b>\n\nこちらから連絡します。",
        'why_price': "❓ <b>NFTでないのにこの価格なのはなぜ？</b>\n\n簡単です。ユーザーネームは単なる文字列ではなく、既製のデジタル資産です。FragmentでNFTとしてミントされていなくても、実際の市場価値を持っています。なぜなら：\n\n1. <b>短い名前は常に不足しています</b> — 作成できず、現在の所有者から購入するしかありません。\n\n2. <b>意味のある名前</b>（TraderTitle, sellerSOL, DHSMarket）— ビジネス、暗号プロジェクト、チャンネル、個人ブランディングのための既製のブランドです。\n\n3. <b>市場価格は需要によって決まります</b> — 譲渡方法ではなく、これらのニックネームへの需要です。Fragmentでは、類似の名前が数千ドルで販売されています（例：@bank, @auto）。私の価格は市場のベンチマークであり、「NFT価格」ではありません。\n\n4. <b>将来の収益化の機会</b> — 購入後、このユーザーネームをFragmentでNFTとしてミントできます（18歳以上でTONウォレットを持っている場合）。",
        'back_to_categories': "🔙 カテゴリに戻る",
        'why_price_btn': "❓ なぜこの価格？",
        'start_shopping_btn': "🛒 ショッピングを始める",
        'channel_btn': "📢 新着情報のチャンネル",
        'contact_btn': "💬 直接交渉",
        'spam_btn': "🚫 スパムブロックあり",
        'ar_warning': "",
        'currency': "$",
        'select_lang': "🌐 言語を選択 / Choose language / اختر اللغة / 選択してください:",
        'lang_selected': "✅ 言語が保存されました！アクションを選択してください。",
    }
}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
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
        "Аниме": "anime",
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

def is_discount_active():
    end_date = datetime(2026, 8, 14, 6, 0, 0)
    return datetime.now() < end_date

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
        result.append(f"{formatted} {currency}")
    return ' / '.join(result) if result else price_text

def format_price(rub_price, lang, ton_price=''):
    if lang == 'ru':
        return f"{rub_price} / {ton_price}" if ton_price else rub_price
    else:
        clean_rub = rub_price.replace(' ', '').replace('₽', '').strip()
        try:
            rub_num = int(clean_rub)
        except:
            rub_num = 0
        usd = round(rub_num / 90, 2)
        return f"${usd} / {ton_price}" if ton_price else f"${usd}"

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if lang is None:
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("🇯🇵 日本語", callback_data="lang_ja")],
        ]
        await update.message.reply_text(
            "🌐 Выберите язык / Choose language / اختر اللغة / 言語を選択してください:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    await show_welcome(update, context, lang)

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    user_id = update.effective_user.id
    set_user_lang(user_id, lang)
    # После сохранения языка показываем приветствие
    await show_welcome(update, context, lang)

async def show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, lang):
    user = update.effective_user
    time_left = get_time_left(lang)
    discount_active = is_discount_active()
    t = TRANSLATIONS[lang]

    if discount_active:
        welcome_text = t['welcome'].format(user=user.first_name, time_left=time_left)
    else:
        welcome_text = t['welcome'].format(user=user.first_name, time_left="")
        welcome_text += "\n\n" + t['no_discount']

    keyboard = [
        [InlineKeyboardButton(t['start_shopping_btn'], callback_data="show_categories")],
        [InlineKeyboardButton(t['channel_btn'], url="https://t.me/EliteTGUsername")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if lang is None:
        # Если язык не сохранён, просим выбрать через /start
        await query.edit_message_text("⚠️ Пожалуйста, выберите язык через /start")
        return
    t = TRANSLATIONS[lang]
    products = load_products()
    DISCOUNT = 25 if is_discount_active() else 0

    if data == "why_price":
        text = t['why_price']
        keyboard = [[InlineKeyboardButton(t['back_to_categories'], callback_data="show_categories")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data == "show_categories":
        time_left = get_time_left(lang)
        discount_active = is_discount_active()
        keyboard = []
        for cat in products.keys():
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        keyboard.append([InlineKeyboardButton(t['why_price_btn'], callback_data="why_price")])
        if discount_active:
            header = t['choose_category'].format(time_left=time_left)
        else:
            header = "📂 <b>Выбери категорию:</b>" if lang == 'ru' else "📂 <b>Choose a category:</b>"
        await query.edit_message_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data.startswith("cat_"):
        category = data[4:]
        items = products.get(category, {})
        stats = load_stats()
        keyboard = []
        for prod_id, info in items.items():
            price_parts = info['price'].split(' / ')
            rub_part = price_parts[0].strip()
            ton_part = price_parts[1].strip() if len(price_parts) > 1 else ''
            if DISCOUNT:
                rub_part = apply_discount(rub_part, DISCOUNT)
                if ton_part:
                    ton_part = apply_discount(ton_part, DISCOUNT)
            price_display = format_price(rub_part, lang, ton_part)
            views = stats.get(prod_id, 0)
            button_text = f"{info['name']} — {price_display} 👁️{views}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"prod_{prod_id}")])
        keyboard.append([InlineKeyboardButton(t['back_to_categories'], callback_data="show_categories")])
        await query.edit_message_text(t['category_items'].format(category=category), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data.startswith("prod_"):
        prod_id = data[5:]
        found = None
        for cat, items in products.items():
            if prod_id in items:
                found = items[prod_id]
                break
        if found:
            views = increment_views(prod_id)
            price_parts = found['price'].split(' / ')
            rub_part = price_parts[0].strip()
            ton_part = price_parts[1].strip() if len(price_parts) > 1 else ''
            if DISCOUNT:
                rub_part = apply_discount(rub_part, DISCOUNT)
                if ton_part:
                    ton_part = apply_discount(ton_part, DISCOUNT)
            price_display = format_price(rub_part, lang, ton_part)
            warning = t['ar_warning'] if lang == 'ar' else ''
            text = t['product_card'].format(name=found['name'], price=price_display, views=views) + warning
            keyboard = [
                [InlineKeyboardButton("🔗 GGSEL", url=found.get("link_ggsel", ""))],
                [InlineKeyboardButton("🔗 PLAYEROK", url=found.get("link_playerok", ""))],
                [InlineKeyboardButton("🔗 STARVELL", url=found.get("link_starvell", ""))],
                [InlineKeyboardButton(t['contact_btn'], callback_data=f"contact_{prod_id}")],
                [InlineKeyboardButton(t['why_price_btn'], callback_data="why_price")],
                [InlineKeyboardButton(t['back_to_categories'], callback_data="show_categories")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Товар не найден.")
        return

    if data.startswith("contact_"):
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
            text = t['contact_admin'].format(contact=CONTACT_USERNAME)
            await query.edit_message_text(text, parse_mode="HTML")
            keyboard = [[InlineKeyboardButton(t['spam_btn'], callback_data=f"spam_{prod_id}")]]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    if data.startswith("spam_"):
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
        await query.edit_message_text(t['spam_block'], parse_mode="HTML")
        return

# ========== АДМИН-ПАНЕЛЬ (сокращённо, т.к. уже была) ==========
# ... (админка оставлена без изменений, она не влияет на языки)

def main():
    _ensure_lang_file()
    init_stats()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_start))
    application.add_handler(CommandHandler("cancel", cancel))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_text))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(admin_|add_cat_|del_|edit_)"))

    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
