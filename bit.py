import os
import asyncio
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "8342079117:AAEm6pYd5FMnNqFkGIlCrHh3epfkU8bOJ1s")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-58a9acbafdea4115a6261c8989289c84")

client = OpenAI(
    api_key="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",  # shu yerga groq key ni qo'y
    base_url="https://api.groq.com/openai/v1"  # ← o'zgardi
)

# Har user uchun tarix va til
histories = {}
user_langs = {}

MAX_HISTORY = 10  # xotira: oxirgi 10 ta xabar

LANG_PROMPTS = {
    "uz": """Sen do'stona va biroz hazilkash AI yordamchisan.
Faqat O'zbek tilida gaplash. Gohida kulgili izoh yoki emoji qo'sh, lekin ko'p emas — faqat o'rinli joylarda.
Qisqa va aniq javob ber. Rasmiy emas, do'stona ohangda.""",

    "ru": """Ты дружелюбный и немного весёлый AI-ассистент.
Отвечай только на русском. Иногда добавляй лёгкую шутку или эмодзи — но в меру, только к месту.
Отвечай коротко и по делу. Тон — дружеский, не официальный.""",

    "en": """You are a friendly and slightly witty AI assistant.
Reply only in English. Occasionally add a light joke or emoji — but not too much, only when it fits naturally.
Keep answers short and helpful. Casual and friendly tone, not formal.""",
}

LANG_NAMES = {
    "uz": "🇺🇿 O'zbek",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

def get_reply(user_id, lang, user_text):
    # Yangi user yoki til o'zgarganda tarixni boshlash
    key = f"{user_id}_{lang}"
    if key not in histories:
        histories[key] = [
            {"role": "system", "content": LANG_PROMPTS[lang]}
        ]

    histories[key].append({"role": "user", "content": user_text})

    # Tarixni MAX_HISTORY bilan cheklash (system prompt saqlanadi)
    if len(histories[key]) > MAX_HISTORY + 1:
        histories[key] = [histories[key][0]] + histories[key][-MAX_HISTORY:]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=histories[key],
        max_tokens=1000
    )

    answer = response.choices[0].message.content
    histories[key].append({"role": "assistant", "content": answer})
    return answer

def lang_keyboard():
    keyboard = [[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if message:
        await message.reply_text(
            "Tilni tanlang / Выберите язык / Choose language:",
            reply_markup=lang_keyboard()
        )

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if message:
        await message.reply_text(
            "Tilni tanlang / Выберите язык / Choose language:",
            reply_markup=lang_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")
    user_id = query.from_user.id
    user_langs[user_id] = lang

    messages = {
        "uz": "✅ Til o'rnatildi: O'zbek 🇺🇿\nEndi menga yozing!",
        "ru": "✅ Язык установлен: Русский 🇷🇺\nТеперь пишите мне!",
        "en": "✅ Language set: English 🇬🇧\nNow send me a message!",
    }

    await query.edit_message_text(messages[lang])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message

    if not message or not message.text:
        return

    user_id = update.effective_user.id

    if user_id not in user_langs:
        await message.reply_text(
            "Avval tilni tanlang / Сначала выберите язык / Please choose a language:",
            reply_markup=lang_keyboard()
        )
        return

    lang = user_langs[user_id]
    user_text = message.text

    await context.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        answer = get_reply(user_id, lang, user_text)
    except Exception as e:
        answer = f"Xatolik: {e}"

    await message.reply_text(answer)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Xatolik: {context.error}")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lan", lang_command))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.add_error_handler(error_handler)

    print("Bot ishga tushdi...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling(allowed_updates=["message", "business_message", "callback_query"])

if __name__ == "__main__":
    main()