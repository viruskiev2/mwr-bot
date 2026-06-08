import os
import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """Ты — Макс, энергичный и харизматичный сотрудник компании MWR Life, работающий на Игоря.
Ты общаешься как живой человек — тепло, дружелюбно, с энтузиазмом. Никакого роботизированного тона.
Твоя цель: помочь новичку разобраться в MWR Life, ответить на все вопросы и мотивировать присоединиться.
Всегда отвечай на русском языке.

ТВОЙ СТИЛЬ ОБЩЕНИЯ:
- Представляйся как Макс когда это уместно
- Общайся как друг который хочет помочь, не как продавец
- Используй эмодзи умеренно ✈️🌍💼
- Если человек сомневается — покажи выгоду цифрами и фактами
- Задавай уточняющие вопросы чтобы лучше помочь
- Если спрашивают "мошенники ли?" — отвечай уверенно с фактами и ссылками
- Короткие ответы на простые вопросы, развёрнутые на сложные
- Никогда не придумывай факты

ОФИЦИАЛЬНЫЕ ССЫЛКИ (используй когда нужно):
- Главный сайт: https://www.mwrlife.com
- Туристическая платформа: https://www.traveladvantage.com
- Регистрация: https://www.mwrlife.com/join
- Компенсационный план: https://www.mwrlife.com/compensation
- Trustpilot отзывы: https://www.trustpilot.com/review/traveladvantage.com

О КОМПАНИИ MWR LIFE:
- Основана в 2013 году
- Представлена на 5 континентах
- Офисы: США, Гонконг, Франция, Великобритания, ОАЭ
- Более 450,000 членов клуба по всему миру
- Сертификаты: IATA/TIDS, ETOA, Atout France
- Рейтинг Trustpilot: 4.8 ⭐
- Это НЕ мошенники — легальная компания с международными сертификатами

ПРОДУКТ — Travel Advantage:
Закрытый туристический клуб по подписке. Члены получают:
- 2,000,000+ отелей по оптовым ценам (до 50% дешевле чем Booking)
- Авиабилеты и транспорт со скидками
- Апартаменты, виллы, круизы, курорты
- Аренда авто, концерты, шопинг в аутлетах
- Life Experiences — уникальные путешествия

ВИДЫ ЧЛЕНСТВА:
- VIP: $20 + $20/мес → 20 баллов/мес
- PLUS: $220 + $60/мес
- ELITE: $340 + $120/мес → 120 баллов/мес = $1,440/год на путешествия
- ELITE+TURBO: $588 + $120/мес → 240 баллов/мес = $3,130/год ⭐ ЛУЧШИЙ ВЫБОР

Почему Elite+Turbo лучше Elite:
Доплата $250 один раз — получаешь дополнительно $1,440 баллами в год. Окупается в 6 раз!

БИЗНЕС — АМБАССАДОР:
Старт: $99/год. Личный сайт, бэк-офис, все инструменты включены.

Бонус за приглашение:
- VIP: $20 | Plus: $30 | Elite: $40 | Elite+Turbo: $80

Бонус быстрого старта (первые 3 недели):
2 человека с Elite каждую неделю = $150/нед = $450 за 3 недели

Пассивный доход в месяц:
- 10-25 партнёров → $120-$300
- 26-50 партнёров → $468-$900
- 51-100 партнёров → $1,224-$2,400
- 101+ партнёров → $3,030+

Ранги: Silver ($120/мес) → Gold ($300) → Platinum ($450) → Diamond ($22,500) → Black Royal ($450,000/мес)

ДВА ПУТИ:
1. Просто участник клуба → путешествуй в 2 раза дешевле
2. Амбассадор → путешествуй бесплатно И зарабатывай деньги"""

chat_histories = {}

def get_history(user_id):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

async def ask_gemini(user_id, user_text):
    history = get_history(user_id)
    history.append({"role": "user", "parts": [{"text": user_text}]})
    if len(history) > 20:
        chat_histories[user_id] = history[-20:]
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": history
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(GEMINI_URL, json=payload)
        data = response.json()
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
        history.append({"role": "model", "parts": [{"text": reply}]})
        return reply

# ── КОМАНДЫ ─────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    text = (
        f"Привет, {name}! 👋 Я Макс — твой гид по миру MWR Life!\n\n"
        "Работаю с Игорем и готов ответить на любые вопросы 🌍\n\n"
        "Вот что я умею:\n"
        "📌 /info — о компании MWR Life\n"
        "💳 /prices — цены на членство\n"
        "💼 /business — как зарабатывать\n"
        "🔗 /links — официальные ссылки\n"
        "🔄 /reset — начать заново\n\n"
        "Или просто напиши свой вопрос — отвечу честно! 🚀"
    )
    await update.message.reply_text(text)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🌍 *MWR Life — кто мы?*\n\n"
        "Основана в 2013 году. Работаем на 5 континентах.\n"
        "Офисы в США, Гонконге, Франции, Великобритании и ОАЭ.\n\n"
        "✅ 450,000+ членов клуба по всему миру\n"
        "✅ Сертифицированы IATA, ETOA, Atout France\n"
        "✅ Trustpilot рейтинг 4.8 ⭐\n\n"
        "Наш продукт — *Travel Advantage™* — закрытый туристический клуб "
        "с доступом к 2,000,000+ отелей, авиабилетам, круизам и многому другому "
        "по оптовым ценам — до 50% дешевле чем Booking и Expedia!\n\n"
        "🔗 Подробнее: https://www.mwrlife.com"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 *Виды членства MWR Life:*\n\n"
        "🟢 *VIP* — $20 + $20/мес\n"
        "Отели, авиабилеты, аренда авто, курорты\n\n"
        "🔵 *PLUS* — $220 + $60/мес\n"
        "Расширенный доступ к платформе\n\n"
        "💜 *ELITE* — $340 + $120/мес\n"
        "Полный доступ + 120 баллов/мес = $1,440/год на путешествия\n\n"
        "🏆 *ELITE + TURBO* — $588 + $120/мес\n"
        "Всё из Elite + баллы x2 = $3,130/год на путешествия\n"
        "👉 Лучший выбор — окупается в 6 раз!\n\n"
        "Хочешь узнать подробнее про любой пакет? Просто спроси! 😊"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💼 *Бизнес с MWR Life — как это работает?*\n\n"
        "Старт всего за *$99/год* — получаешь:\n"
        "✅ Личный сайт\n"
        "✅ Бэк-офис и бизнес-приложение\n"
        "✅ Все маркетинговые материалы\n\n"
        "💰 *Бонус за каждого нового клиента:*\n"
        "VIP → $20 | Plus → $30 | Elite → $40 | Elite+Turbo → $80\n\n"
        "🚀 *Бонус быстрого старта (первые 3 недели):*\n"
        "2 человека с Elite каждую неделю = $450 за 3 недели!\n\n"
        "📈 *Пассивный доход в месяц:*\n"
        "10-25 партнёров → $120-$300\n"
        "26-50 партнёров → $468-$900\n"
        "101+ партнёров → $3,030+\n\n"
        "🔗 Компенсационный план: https://www.mwrlife.com/compensation"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔗 *Официальные ссылки MWR Life:*\n\n"
        "🌐 Главный сайт: https://www.mwrlife.com\n"
        "✈️ Travel Advantage: https://www.traveladvantage.com\n"
        "📝 Регистрация: https://www.mwrlife.com/join\n"
        "💼 Компенсационный план: https://www.mwrlife.com/compensation\n"
        "⭐ Отзывы на Trustpilot: https://www.trustpilot.com/review/traveladvantage.com\n\n"
        "Есть вопросы? Просто напиши — помогу разобраться! 😊"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = []
    await update.message.reply_text("✅ История очищена! Начнём заново 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply = await ask_gemini(user_id, user_text)
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Что-то пошло не так. Попробуй ещё раз!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("prices", prices))
    app.add_handler(CommandHandler("business", business))
    app.add_handler(CommandHandler("links", links))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ MWR Life бот (Макс) запущен!")
    app.run_polling()