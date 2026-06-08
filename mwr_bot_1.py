import os
import logging
import httpx
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# =====================================================================
# 1. НАСТРОЙКА ВЕБ-СЕРВЕРА FLASK
# =====================================================================
# Создаем экземпляр веб-приложения Flask. Переменная flask_app — это точка входа 
# для внешнего сервера Gunicorn на платформе Render.
flask_app = Flask(__name__)

# Декоратор @flask_app.route('/') связывает корневой URL-адрес (/) с функцией home().
# Когда cron-job.org делает запрос к сайту, Flask выполняет этот код.
@flask_app.route('/')
def home():
    # Возвращаем текстовый ответ и HTTP-статус 200 (OK). 
    # Это говорит серверу Render: "Я живой, не усыпляй меня!"
    return "Бот активен и работает! 🚀", 200

# =====================================================================
# 2. ПОЛУЧЕНИЕ НАСТРОЕК (ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ)
# =====================================================================
# os.environ.get вытягивает секретные ключи из настроек операционной системы (на Render).
# Это базовая практика безопасности (Best Practice), чтобы не палить токены в коде на GitHub.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Включаем базовое логирование. Оно выводит системные сообщения и ошибки в консоль Render.
logging.basicConfig(level=logging.INFO)

# Исходные данные для ИИ (Промпт) — это база знаний, которая задает жесткие рамки,
# роль (Макс) и правила поведения для нейросети при каждом запросе.
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
Why Turbo: доплата $250 один раз = +$1,440 в год. Окупается в 6 раз!

БИЗНЕС:
Старт $99/год. Бонус за приглашение: VIP $20, Plus $30, Elite $40, Elite+Turbo $80
Быстрый старт: 2 человека с Elite/неделю = $450 за 3 недели
Пассивный доход: 10-25 партнёров $120-300/мес, 101+ партнёров $3,030+/мес"""

# =====================================================================
# 3. УПРАВЛЕНИЕ ДИАЛОГАМИ (ПАМЯТЬ БОТА)
# =====================================================================
# Словарь (Dictionary) для хранения истории переписки. Ключ — ID пользователя, 
# значение — список (List) сообщений. Память сотрется при перезапуске сервера.
chat_histories = {}

def get_history(user_id):
    """Функция проверяет: если пользователя нет в словаре памяти, создает ему пустой список"""
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

# =====================================================================
# 4. ИНТЕГРАЦИЯ С НЕЙРОСЕТЬЮ (НЕЙРОНКА / ИИ)
# =====================================================================
# Ключевое слово `async` делает функцию асинхронной. Она умеет "ставить себя на паузу",
# пока ждет ответа от ИИ, не блокируя выполнение остального кода.
async def ask_ai(user_id, user_text):
    # Получаем текущую историю диалога для конкретного юзера
    history = get_history(user_id)
    # Добавляем новое сообщение пользователя в историю
    history.append({"role": "user", "content": user_text})
    
    # Слайсинг (history[-20:]). Если сообщений больше 20, оставляем только последние 20,
    # чтобы не переплачивать за размер запроса (токены) в OpenRouter.
    if len(history) > 20:
        chat_histories[user_id] = history[-20:]

    # Собираем полный контекст: сначала системные правила, потом история реплик
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # `async with` гарантирует, что HTTP-клиент корректно закроет соединение после выполнения.
    # httpx.AsyncClient используется для асинхронных запросов к внешним API.
    async with httpx.AsyncClient(timeout=30) as client:
        # Отправляем POST-запрос на сервера OpenRouter
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
        # Парсим (распаковываем) полученный ответ из формата JSON в Python-словарь
        data = response.json()
        # Вытаскиваем точечный текст ответа нейросети из структуры JSON
        reply = data["choices"][0]["message"]["content"]
        # Добавляем ответ ИИ в историю, чтобы бот помнил, что он сам ответил юзеру
        history.append({"role": "assistant", "content": reply})
        return reply

# =====================================================================
# 5. ОБРАБОТЧИКИ КОМАНД ТЕЛЕГРАМ (ХЕНДЛЕРЫ)
# =====================================================================
# Все функции обработки команд принимают два обязательных объекта библиотеки python-telegram-bot:
# Update (данные о сообщении) и Context (вспомогательные инструменты библиотеки).
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
    # Полностью очищаем список истории диалога для данного пользователя
    chat_histories[update.effective_user.id] = []
    await update.message.reply_text("✅ История очищена! Начнём заново 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Этот хендлер ловит любой обычный текст, который НЕ является командой"""
    user_id = update.effective_user.id
    user_text = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        reply = await ask_ai(user_id, user_text)
        await update.message.reply_text(reply)
    except Exception as e:
        # Теперь мы не просто пишем "Ошибка", а выводим максимум инфы в логи Render
        logging.error(f"⚠️ Произошла ошибка при запросе к ИИ: {e}")
        
        # Если ошибка связана с 'choices', мы проверяем, не сломалась ли история
        if "chat_histories" in globals() and user_id in chat_histories:
            logging.info(f"Последний статус истории для юзера: {chat_histories[user_id][-1:]}")
            
        await update.message.reply_text("⚠️ Сервер ИИ временно перегружен или недоступен. Попробуй задать вопрос ещё раз!")

# =====================================================================
# 6. ИНЖЕНЕРНАЯ МАГИЯ ЗАПУСКА ПОТОКОВ (ДЛЯ ДЕПЛОЯ И СЕМЕСТРА)
# =====================================================================
def start_bot_in_thread():
    """
    Эта функция запускает Телеграм-бота. На Render её вызывает фоновый поток (Thread).
    Поскольку бот асинхронный, нам приходится вручную создавать для него Event Loop (цикл событий).
    """
    # 1. Создаем изолированный цикл событий asyncio для этого отдельного потока
    loop = asyncio.new_event_loop()
    # 2. Устанавливаем его как активный для текущего потока
    asyncio.set_event_loop(loop)
    
    # Настраиваем конфигурацию бота через паттерн Builder (Строитель)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем хендлеры (какая функция за какую команду отвечает)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("prices", prices))
    app.add_handler(CommandHandler("business", business))
    app.add_handler(CommandHandler("links", links))
    app.add_handler(CommandHandler("reset", reset))
    # Регистрируем перехватчик любого текста. Фильтр `~filters.COMMAND` означает "НЕ команда"
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот инициализирован внутри потока Gunicorn!")
    
    # ИСПРАВЛЕНО ЗДЕСЬ: добавили stop_signals=None. 
    # Это запрещает боту перехватывать системные сигналы Linux из фонового потока, 
    # благодаря чему он больше не будет падать в RuntimeError на сервере Render.
    loop.run_until_complete(app.run_polling(close_loop=False, stop_signals=None))

# === ТОЧКА СВЯЗКИ С GUNICORN ===
# Создаем объект Thread (Поток). Мы выделяем боту персональное "ядро" (поток выполнения).
# target=start_bot_in_thread указывает, какую функцию запустить в потоке.
# daemon=True означает, что если закроется основной сервер Flask, поток бота закроется автоматически.
bot_thread = Thread(target=start_bot_in_thread, daemon=True)
# Запускаем созданный фоновый поток.
bot_thread.start()
print("✅ Фоновый поток для Телеграм-бота успешно запущен!")

# Стандартная конструкция Python. Код внутри выполнится ТОЛЬКО если запустить файл 
# напрямую руками: `python mwr_bot_1.py`. 
# При импорте веб-сервером Gunicorn этот блок игнорируется.
if __name__ == "__main__":
    # Получаем порт от Render или ставим по умолчанию 8080 (для локальных тестов)
    port = int(os.environ.get("PORT", 8080))
    # Запускаем Flask локально в основном потоке выполнения
    flask_app.run(host="0.0.0.0", port=port)