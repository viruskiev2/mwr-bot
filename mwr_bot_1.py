import os
import logging
import httpx
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# =====================================================================
# 1. FLASK ВЕБ-СЕРВЕР (keep-alive для Render)
# =====================================================================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Макс активен и готов помогать! 🚀", 200

# =====================================================================
# 2. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# =====================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)

# =====================================================================
# 3. СИСТЕМА ЗНАНИЙ (ПРОМПТ)
# =====================================================================
SYSTEM_PROMPT = """Ты — Макс, энергичный сотрудник компании MWR Life, работающий на Игоря.
Общайся как живой человек — тепло, дружелюбно, с энтузиазмом. Никаких роботов!
Цель: помочь разобраться в MWR Life и мотивировать присоединиться.
ВСЕГДА отвечай на русском языке.

ТВОЙ СТИЛЬ:
- Друг который помогает, не продавец
- Эмодзи умеренно ✈️🌍💼
- Если сомнение → показываешь ФАКТЫ и ссылки
- Задаёшь вопросы чтобы лучше помочь
- На "мошенники?" → уверенно: легальная компания, сертификаты IATA/ETOA

ОФИЦИАЛЬНЫЕ ССЫЛКИ:
- https://www.mwrlife.com
- https://www.traveladvantage.com
- https://www.mwrlife.com/join

О КОМПАНИИ:
Основана 2013, 5 континентов, офисы в США/Гонконг/Франция/Великобритания/ОАЭ
450,000+ членов, сертификаты IATA/TIDS/ETOA/Atout France, Trustpilot 4.8★
НЕ мошенники — легальная компания с международными сертификатами

ЧЛЕНСТВО (Travel Advantage™ — закрытый клуб с 2,000,000+ отелей):
- VIP: $20 + $20/мес → 20 баллов/мес
- PLUS: $220 + $60/мес
- ELITE: $340 + $120/мес → 120 баллов/мес = $1,440/год на путешествия
- ELITE+TURBO: $588 + $120/мес → 240 баллов/мес = $3,130/год ⭐ ЛУЧШИЙ ВЫБОР
  Почему: доплата $250 один раз → получаешь +$1,440 в год. Окупается в 6 раз!

БИЗНЕС (Амбассадор, старт $99/год):
Бонус за клиента: VIP $20, Plus $30, Elite $40, Elite+Turbo $80
Быстрый старт: 2 человека с Elite/неделю = $450 за 3 недели
Пассивный доход: 10-25 партнёров $120-300/мес, 101+ партнёров $3,030+/мес"""

# =====================================================================
# 4. ПАМЯТЬ ДИАЛОГОВ
# =====================================================================
chat_histories = {}

def get_history(user_id):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

# =====================================================================
# 5. ИИ (GROQ)
# =====================================================================
async def ask_ai(user_id, user_text):
    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})
    
    if len(history) > 20:
        chat_histories[user_id] = history[-20:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
        )
        
        data = response.json()
        
        if "error" in data:
            error_msg = data["error"].get("message", "Неизвестная ошибка")
            raise RuntimeError(f"Groq Error: {error_msg}")
            
        reply = data["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        return reply

# =====================================================================
# 6. КОМАНДЫ TELEGRAM
# =====================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    text = (
        f"Привет, {name}! 👋 Я Макс — твой гид по MWR Life!\n\n"
        "Работаю с Игорем и готов ответить на ВСЕ вопросы 🌍\n\n"
        "Команды:\n"
        "📌 /info — о компании\n"
        "💳 /prices — цены на членство\n"
        "💼 /business — как зарабатывать\n"
        "🔗 /links — официальные ссылки\n"
        "🔄 /reset — очистить историю\n\n"
        "Или просто напиши вопрос — отвечу честно! 🚀"
    )
    await update.message.reply_text(text)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🌍 *MWR Life*\n\n"
        "Основана в 2013 году. Работаем на 5 континентах.\n"
        "Офисы в США, Гонконге, Франции, Великобритании и ОАЭ.\n\n"
        "✅ 450,000+ членов по всему миру\n"
        "✅ Сертифицированы: IATA, ETOA, Atout France\n"
        "✅ Trustpilot: 4.8 ⭐\n\n"
        "Продукт: Travel Advantage™\n"
        "Закрытый туристический клуб с доступом к 2,000,000+ отелей по оптовым ценам (до 50% дешевле Booking).\n\n"
        "🔗 https://www.mwrlife.com"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 *Виды членства:*\n\n"
        "🟢 *VIP* — $20 + $20/мес\n\n"
        "🔵 *PLUS* — $220 + $60/мес\n\n"
        "💜 *ELITE* — $340 + $120/мес\n"
        "→ 120 баллов/мес = $1,440/год на путешествия\n\n"
        "🏆 *ELITE + TURBO* — $588 + $120/мес ⭐\n"
        "→ 240 баллов/мес = $3,130/год на путешествия\n"
        "→ Доплата $250 один раз окупается в 6 раз!\n\n"
        "Хочешь узнать подробнее? Спроси! 😊"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💼 *Бизнес с MWR Life*\n\n"
        "Старт: всего $99/год\n"
        "Получаешь: сайт, приложение, маркетинг-материалы\n\n"
        "💰 *Бонус за каждого клиента:*\n"
        "VIP → $20 | Plus → $30 | Elite → $40 | Elite+Turbo → $80\n\n"
        "🚀 *Быстрый старт (первые 3 недели):*\n"
        "2 человека с Elite/неделю = $450 за 3 недели!\n\n"
        "📈 *Пассивный доход в месяц:*\n"
        "10-25 партнёров → $120-300\n"
        "26-50 партнёров → $468-900\n"
        "101+ партнёров → $3,030+\n\n"
        "🔗 https://www.mwrlife.com/compensation"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔗 *Официальные ссылки:*\n\n"
        "🌐 https://www.mwrlife.com\n"
        "✈️ https://www.traveladvantage.com\n"
        "📝 https://www.mwrlife.com/join\n"
        "💼 https://www.mwrlife.com/compensation\n"
        "⭐ https://www.trustpilot.com/review/traveladvantage.com"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_histories[update.effective_user.id] = []
    await update.message.reply_text("✅ История очищена! 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        reply = await ask_ai(user_id, user_text)
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)[:150]}", parse_mode="Markdown")

# =====================================================================
# 7. ЗАПУСК БОТА В ФОНОВОМ ПОТОКЕ
# =====================================================================
def start_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("prices", prices))
    app.add_handler(CommandHandler("business", business))
    app.add_handler(CommandHandler("links", links))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Макс запущен на Groq и готов общаться!")
    loop.run_until_complete(app.run_polling(close_loop=False, stop_signals=None))

bot_thread = Thread(target=start_bot_in_thread, daemon=True)
bot_thread.start()

# =====================================================================
# 8. ЗАПУСК FLASK
# =====================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, debug=False)