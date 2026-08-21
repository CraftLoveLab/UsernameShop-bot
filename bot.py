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
        'price_format': "{rub} ₽ / {ton} TON",
        'ton_price': "{ton} TON",
        'select_lang': "🌐 Выберите язык / Choose language / اختر اللغة / 言語を選択してください:",
        # админка (всегда на русском)
        'admin_password_prompt': "🔐 Введите пароль для входа в админ-панель:",
        'admin_wrong_password': "❌ Неверный пароль. Попробуйте /admin",
        'admin_denied': "⛔ Доступ запрещён. Введите /admin",
        'admin_menu': "🛠 <b>Админ-панель</b>\nВыберите действие:",
        'admin_add': "➕ Добавить товар",
        'admin_remove': "➖ Удалить товар",
        'admin_edit': "✏️ Изменить цену",
        'admin_stats': "📊 Статистика",
        'admin_logs': "📜 История действий",
        'admin_close': "❌ Закрыть админку",
        'admin_cancel': "✅ Операция отменена.",
        'admin_closed': "🔒 Админ-панель закрыта.",
        'admin_add_category': "Выберите категорию:",
        'admin_add_enter_id': "Введите ID для нового товара (например, user45, garant13, crypto23):",
        'admin_add_enter_name': "Введите название товара (например, @Test):",
        'admin_add_enter_price': "Введите цену (например, '1000 ₽ / 8 TON'):",
        'admin_add_enter_gg': "Введите ссылку GGSEL (или '-' если нет):",
        'admin_add_enter_playerok': "Введите ссылку PLAYEROK (или '-' если нет):",
        'admin_add_enter_starvell': "Введите ссылку STARVELL (или '-' если нет):",
        'admin_add_success': "✅ Товар {name} добавлен в категорию {category}!",
        'admin_remove_select': "Выберите товар для удаления:",
        'admin_remove_success': "✅ Товар {name} удалён.",
        'admin_edit_select': "Выберите товар для изменения цены:",
        'admin_edit_prompt': "Введите новую цену для товара (в формате 'X ₽ / Y TON', например '1500 ₽ / 13 TON'):",
        'admin_edit_success': "✅ Цена для {pid} обновлена на {new_price}",
        'admin_stats_text': "📊 <b>Статистика просмотров</b>\n\nВсего просмотров: {total}\n\n{top}",
        'admin_logs_empty': "📜 История действий пуста.",
        'admin_logs_text': "📜 <b>Последние действия:</b>\n\n{logs}",
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
        'price_format': "${usd} / {ton} TON",
        'ton_price': "{ton} TON",
        'select_lang': "🌐 Select language / Choose language / اختر اللغة / 言語を選択してください:",
        'admin_password_prompt': "🔐 Enter password to access admin panel:",
        'admin_wrong_password': "❌ Wrong password. Try /admin",
        'admin_denied': "⛔ Access denied. Type /admin",
        'admin_menu': "🛠 <b>Admin panel</b>\nChoose action:",
        'admin_add': "➕ Add product",
        'admin_remove': "➖ Remove product",
        'admin_edit': "✏️ Edit price",
        'admin_stats': "📊 Statistics",
        'admin_logs': "📜 History",
        'admin_close': "❌ Close admin",
        'admin_cancel': "✅ Operation cancelled.",
        'admin_closed': "🔒 Admin panel closed.",
        'admin_add_category': "Choose category:",
        'admin_add_enter_id': "Enter ID for new product (e.g., user45, garant13, crypto23):",
        'admin_add_enter_name': "Enter product name (e.g., @Test):",
        'admin_add_enter_price': "Enter price (e.g., '1000 ₽ / 8 TON'):",
        'admin_add_enter_gg': "Enter GGSEL link (or '-' if none):",
        'admin_add_enter_playerok': "Enter PLAYEROK link (or '-' if none):",
        'admin_add_enter_starvell': "Enter STARVELL link (or '-' if none):",
        'admin_add_success': "✅ Product {name} added to category {category}!",
        'admin_remove_select': "Select product to remove:",
        'admin_remove_success': "✅ Product {name} removed.",
        'admin_edit_select': "Select product to edit price:",
        'admin_edit_prompt': "Enter new price (format 'X ₽ / Y TON', e.g., '1500 ₽ / 13 TON'):",
        'admin_edit_success': "✅ Price for {pid} updated to {new_price}",
        'admin_stats_text': "📊 <b>Views statistics</b>\n\nTotal views: {total}\n\n{top}",
        'admin_logs_empty': "📜 History is empty.",
        'admin_logs_text': "📜 <b>Last actions:</b>\n\n{logs}",
    },
    'ar': {
        # аналогично, на арабском
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
        'price_format': "${usd} / {ton} TON",
        'ton_price': "{ton} TON",
        'select_lang': "🌐 اختر اللغة / Choose language / Select language / 言語を選択してください:",
        # админка на арабском (можно оставить русским или английским, но для упрощения оставлю русский для админа, так как админ один)
        'admin_password_prompt': "🔐 أدخل كلمة المرور للوصول إلى لوحة التحكم:",
        'admin_wrong_password': "❌ كلمة مرور خاطئة. جرب /admin",
        'admin_denied': "⛔ تم رفض الوصول. اكتب /admin",
        'admin_menu': "🛠 <b>لوحة التحكم</b>\nاختر إجراء:",
        'admin_add': "➕ إضافة منتج",
        'admin_remove': "➖ حذف منتج",
        'admin_edit': "✏️ تعديل السعر",
        'admin_stats': "📊 الإحصائيات",
        'admin_logs': "📜 السجل",
        'admin_close': "❌ إغلاق لوحة التحكم",
        'admin_cancel': "✅ تم إلغاء العملية.",
        'admin_closed': "🔒 تم إغلاق لوحة التحكم.",
        'admin_add_category': "اختر الفئة:",
        'admin_add_enter_id': "أدخل معرف المنتج الجديد (مثل user45, garant13, crypto23):",
        'admin_add_enter_name': "أدخل اسم المنتج (مثل @Test):",
        'admin_add_enter_price': "أدخل السعر (مثل '1000 ₽ / 8 TON'):",
        'admin_add_enter_gg': "أدخل رابط GGSEL (أو '-' إذا لم يوجد):",
        'admin_add_enter_playerok': "أدخل رابط PLAYEROK (أو '-' إذا لم يوجد):",
        'admin_add_enter_starvell': "أدخل رابط STARVELL (أو '-' إذا لم يوجد):",
        'admin_add_success': "✅ تم إضافة المنتج {name} إلى الفئة {category}!",
        'admin_remove_select': "اختر المنتج للحذف:",
        'admin_remove_success': "✅ تم حذف المنتج {name}.",
        'admin_edit_select': "اختر المنتج لتعديل السعر:",
        'admin_edit_prompt': "أدخل السعر الجديد (بصيغة 'X ₽ / Y TON'، مثلاً '1500 ₽ / 13 TON'):",
        'admin_edit_success': "✅ تم تحديث سعر {pid} إلى {new_price}",
        'admin_stats_text': "📊 <b>إحصائيات المشاهدات</b>\n\nإجمالي المشاهدات: {total}\n\n{top}",
        'admin_logs_empty': "📜 السجل فارغ.",
        'admin_logs_text': "📜 <b>آخر الإجراءات:</b>\n\n{logs}",
    },
    'ja': {
        # аналогично, на японском (кратко)
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
        'price_format': "${usd} / {ton} TON",
        'ton_price': "{ton} TON",
        'select_lang': "🌐 言語を選択 / Choose language / اختر اللغة / 選択してください:",
        'admin_password_prompt': "🔐 管理者パネルにアクセスするためのパスワードを入力してください:",
        'admin_wrong_password': "❌ パスワードが間違っています。 /admin を試してください",
        'admin_denied': "⛔ アクセスが拒否されました。 /admin と入力してください",
        'admin_menu': "🛠 <b>管理者パネル</b>\nアクションを選択してください:",
        'admin_add': "➕ 商品を追加",
        'admin_remove': "➖ 商品を削除",
        'admin_edit': "✏️ 価格を編集",
        'admin_stats': "📊 統計",
        'admin_logs': "📜 履歴",
        'admin_close': "❌ 管理者パネルを閉じる",
        'admin_cancel': "✅ 操作がキャンセルされました。",
        'admin_closed': "🔒 管理者パネルが閉じられました。",
        'admin_add_category': "カテゴリを選択してください:",
        'admin_add_enter_id': "新しい商品のIDを入力してください（例: user45, garant13, crypto23）:",
        'admin_add_enter_name': "商品名を入力してください（例: @Test）:",
        'admin_add_enter_price': "価格を入力してください（例: '1000 ₽ / 8 TON'）:",
        'admin_add_enter_gg': "GGSELリンクを入力してください（ない場合は '-'）:",
        'admin_add_enter_playerok': "PLAYEROKリンクを入力してください（ない場合は '-'）:",
        'admin_add_enter_starvell': "STARVELLリンクを入力してください（ない場合は '-'）:",
        'admin_add_success': "✅ 商品 {name} がカテゴリ {category} に追加されました！",
        'admin_remove_select': "削除する商品を選択してください:",
        'admin_remove_success': "✅ 商品 {name} が削除されました。",
        'admin_edit_select': "価格を編集する商品を選択してください:",
        'admin_edit_prompt': "新しい価格を入力してください（形式 'X ₽ / Y TON'、例: '1500 ₽ / 13 TON'）:",
        'admin_edit_success': "✅ {pid} の価格が {new_price} に更新されました",
        'admin_stats_text': "📊 <b>閲覧統計</b>\n\n総閲覧数: {total}\n\n{top}",
        'admin_logs_empty': "📜 履歴は空です。",
        'admin_logs_text': "📜 <b>最後のアクション:</b>\n\n{logs}",
    }
}

# ========== РАБОТА С ЯЗЫКОМ ==========
def get_user_lang(user_id):
    try:
        with open("user_lang.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id))
    except FileNotFoundError:
        return None

def set_user_lang(user_id, lang):
    try:
        with open("user_lang.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    data[str(user_id)] = lang
    with open("user_lang.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
        await update.message.reply_text("🌐 Выберите язык / Choose language / اختر اللغة / 言語を選択してください:", reply_markup=InlineKeyboardMarkup(keyboard))
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
        await update.callback_query.edit_message_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if lang is None:
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

# ========== АДМИН-ПАНЕЛЬ ==========
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Админка всегда на русском (или на языке админа, но для простоты оставляем русский)
    await update.message.reply_text("🔐 Введите пароль для входа в админ-панель:")
    context.user_data['admin_waiting_password'] = True

async def admin_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    username = update.effective_user.username or update.effective_user.first_name

    if context.user_data.get('admin_waiting_password'):
        if text == ADMIN_PASSWORD:
            context.user_data['admin_waiting_password'] = False
            context.user_data['admin_authenticated'] = True
            await show_admin_menu(update, context)
        else:
            await update.message.reply_text("❌ Неверный пароль. Попробуйте /admin")
        return

    if not context.user_data.get('admin_authenticated'):
        await update.message.reply_text("⛔ Доступ запрещён. Введите /admin")
        return

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
            [InlineKeyboardButton("🎌 Аниме", callback_data="add_cat_Аниме")],
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
        await query.edit_message_text("Введите новую цену для товара (в формате 'X ₽ / Y TON', например '1500 ₽ / 13 TON'):")
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
    context.user_data.clear()
    await update.message.reply_text("✅ Операция отменена.")

# ========== ЗАПУСК ==========
def main():
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
