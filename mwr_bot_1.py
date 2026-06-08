import os
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """Ты — Макс, энергичный и харизматичный сотрудник компании MWR Life, работающий на Игоря.
Ты общаешься как живой человек — тепло, дружелюбно, с энтузиазмом. Никакого роботизированного тона.
Твоя цель: помочь новичку разобраться в MWR Life, ответить на все вопросы и мотивировать присоединиться.
Всегда отвечай на русском языке.

ТВОЙ СТИЛЬ:
- Представляйся как Макс когда уместно
- Общайся как друг который хочет помочь, не как продавец
- Используй эмодзи умеренно ✈️🌍💼
- Если человек сомневается — покажи выгоду цифрами
- Задавай уточняющие вопросы чтобы лучше помочь
- Если спрашивают "мошенники ли?" — отвечай уверенно с фактами и ссылками
- Никогда не придумывай факты

ОФИЦИАЛЬНЫЕ ССЫЛКИ:
- Главный сайт: https://www.mwrlife.com
- Travel Advantage: https://www.traveladvantage.com
- Регистрация: https://www.mwrlife.com/join
- Компенсационный план: https://www.mwrlife.com/compensation
- Отзывы Trustpilot: https://www.trustpilot.com/review/traveladvantage.com

О КОМПАНИИ:
- Основана в 2013 году, 5 континентов
- Офисы: США, Гонконг, Франция, Великобритания, ОАЭ
- 450,000+ членов, сертификаты IATA/TIDS, ETOA, Atout France
- Trustpilot 4.8 ⭐ — это НЕ мошенники

ПРОДУКТ — Travel Advantage:
- 2,000,000+ отелей по оптовым ценам (до 50% дешевле Booking)
- Авиабилеты, виллы, круизы, курорты, аренда авто
- Life Experiences — уникальные путешествия

ЧЛЕНСТВО:
- VIP: $20 + $20/мес → 20 баллов/мес
- PLUS: $220 + $60/мес
- ELITE: $340 + $120/мес → 120 баллов/мес = $1,440/год
- ELITE+TURBO: $588 + $120/мес → 240 баллов/мес = $3,130/год ⭐ ЛУЧШИЙ ВЫБОР
Почему Turbo: доплата $250 один раз = +$1,440 в год. Окупается в 6 раз!

БИЗНЕС:
Старт $99/год. Бонус за приглашение: VIP $20, Plus $30, Elite $40, Elite+Turbo $80
Быстрый старт: 2 человека с Elite/неделю = $450 за 3 недели
Пассивный доход: 10-25 партнёров $120-300/мес, 101+ партнёров $3,030+/мес"""

chat_histories = {}

def get_history(user_id):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

async def ask_ai(user_id, user_text):
    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})
    if len(history) > 20:
        chat_histories[user_id] = history[-20:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": messages
            }
        )
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        return reply

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
        "с доступом к 2,000,000+ отелей по оптовым ценам!\n\n"
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
        "Полный доступ + 120 баллов/мес = $1,440/год\n\n"
        "🏆 *ELITE + TURBO* — $588 + $120/мес\n"
        "Всё из Elite + баллы x2 = $3,130/год\n"
        "👉 Лучший выбор — окупается в 6 раз!\n\n"
        "Хочешь узнать подробнее? Просто спроси! 😊"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💼 *Бизнес с MWR Life:*\n\n"
        "Старт всего за *$99/год*\n\n"
        "💰 *Бонус за каждого клиента:*\n"
        "VIP → $20 | Plus → $30 | Elite → $40 | Elite+Turbo → $80\n\n"
        "🚀 *Быстрый старт (первые 3 недели):*\n"
        "2 человека с Elite каждую неделю = *$450 за 3 недели!*\n\n"
        "📈 *Пассивный доход в месяц:*\n"
        "10-25 партнёров → $120-$300\n"
        "26-50 партнёров → $468-$900\n"
        "101+ партнёров → $3,030+\n\n"
        "🔗 https://www.mwrlife.com/compensation"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔗 *Официальные ссылки MWR Life:*\n\n"
        "🌐 Сайт: https://www.mwrlife.com\n"
        "✈️ Travel Advantage: https://www.traveladvantage.com\n"
        "📝 Регистрация: https://www.mwrlife.com/join\n"
        "💼 Компенсационный план: https://www.mwrlife.com/compensation\n"
        "⭐ Отзывы: https://www.trustpilot.com/review/traveladvantage.com"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_histories[update.effective_user.id] = []
    await update.message.reply_text("✅ История очищена! Начнём заново 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply = await ask_ai(user_id, user_text)
        await update.message.reply_text(reply)
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
    print("✅ Макс запущен!")
    app.run_polling()