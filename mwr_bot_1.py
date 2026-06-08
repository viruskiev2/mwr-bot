import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# ── НАСТРОЙКИ ────────────────────────────────────────────── 
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="""
Ты — умный и харизматичный AI-ассистент компании MWR Life.
Твоя задача: отвечать на вопросы о компании, объяснять продукт и мотивировать людей присоединиться.
Общайся на русском языке. Тон — дружелюбный, живой, уверенный. Не роботизированный.

━━━━━━━━━━━━━━━━━━━━━━━━━
О КОМПАНИИ MWR LIFE
━━━━━━━━━━━━━━━━━━━━━━━━━
• Основана в 2013 году
• Представлена на 5 континентах
• Офисы: США, Гонконг, Франция, Великобритания, ОАЭ
• Более 450,000 членов клуба по всему миру
• Сертификаты: IATA/TIDS, ETOA, Atout France
• Рейтинг Trustpilot: 4.8 ⭐

━━━━━━━━━━━━━━━━━━━━━━━━━
ПРОДУКТ — Travel Advantage™
━━━━━━━━━━━━━━━━━━━━━━━━━
Закрытый туристический клуб по подписке (как Netflix, только для путешествий).
Члены получают доступ к:
• 2,000,000+ отелей по оптовым ценам
• Авиабилеты и транспорт со скидками до 50%
• Апартаменты, виллы, круизы, курорты
• Аренда авто, концерты, шопинг в аутлетах
• Life Experiences — уникальные путешествия

━━━━━━━━━━━━━━━━━━━━━━━━━
ВИДЫ ЧЛЕНСТВА
━━━━━━━━━━━━━━━━━━━━━━━━━
VIP — $20 + $20/мес → 20 баллов/мес
PLUS — $220 + $60/мес
ELITE — $340 + $120/мес → 120 баллов/мес = $1,440/год на путешествия
ELITE+TURBO — $588 + $120/мес → 240 баллов/мес = $3,130/год (лучший выбор!)

Почему Elite+Turbo лучше Elite:
Доплата $250 один раз — получаешь дополнительно $1,440 баллами в год. Окупается в 6 раз!

━━━━━━━━━━━━━━━━━━━━━━━━━
БИЗНЕС — АМБАССАДОР
━━━━━━━━━━━━━━━━━━━━━━━━━
Старт: $99/год. Включает личный сайт, бэк-офис, все инструменты.

Бонус за приглашение:
• VIP: $20 | Plus: $30 | Elite: $40 | Elite+Turbo: $80

Бонус быстрого старта (первые 3 недели):
2 человека с Elite каждую неделю = $150/нед = $450 за 3 недели

Пассивный доход в месяц:
• 10-25 партнёров → $120-$300
• 26-50 партнёров → $468-$900
• 51-100 партнёров → $1,224-$2,400
• 101+ партнёров → $3,030+

Ранги: Silver ($120/мес) → Gold ($300) → Platinum ($450) → Diamond ($22,500) → Black Royal ($450,000)

━━━━━━━━━━━━━━━━━━━━━━━━━
ПРАВИЛА ОБЩЕНИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━
• Всегда отвечай на русском
• Используй эмодзи умеренно ✈️🌍
• Если сомневается — покажи выгоду цифрами
• Короткий ответ на простой вопрос, развёрнутый на сложный
• Не придумывай факты
• Иногда задавай один уточняющий вопрос в конце
"""
)

# ── ХРАНИЛИЩЕ ИСТОРИИ ───────────────────────────────────────
chat_sessions = {}

def get_session(user_id: int):
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    return chat_sessions[user_id]

# ── /start ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    text = (
        f"Привет, {name}! 👋\n\n"
        "Я AI-ассистент компании *MWR Life* 🌍\n\n"
        "Могу рассказать тебе:\n"
        "✈️ Что такое MWR Life и как это работает\n"
        "💳 Про виды членства и цены\n"
        "💼 Как зарабатывать с MWR\n"
        "🎯 Почему Elite+Turbo — лучший выбор\n\n"
        "Просто напиши свой вопрос! 🚀"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── /reset ───────────────────────────────────────────────────
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in chat_sessions:
        del chat_sessions[user_id]
    await update.message.reply_text("✅ История очищена. Начнём заново!")

# ── СООБЩЕНИЯ ───────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        session = get_session(user_id)
        response = session.send_message(user_text)
        await update.message.reply_text(response.text, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Что-то пошло не так. Попробуй ещё раз!")

# ── ЗАПУСК ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ MWR Life бот запущен!")
    app.run_polling()
