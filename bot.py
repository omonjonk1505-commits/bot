import os
import asyncio
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "8342079117:AAEm6pYd5FMnNqFkGIlCrHh3epfkU8bOJ1s")

client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

# Har user uchun tarix va til
histories = {}
user_langs = {}

MAX_HISTORY = 10

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

# ============================================================
# KEYBOARD HELPERS
# ============================================================

def lang_keyboard():
    """Inline keyboard — til tanlash"""
    keyboard = [[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def main_reply_keyboard():
    """Doimiy reply keyboard — asosiy menyu"""
    keyboard = [
        [KeyboardButton("🎮 O'yinlar"), KeyboardButton("🌐 Til o'zgartirish")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True, one_time_keyboard=False)


def games_reply_keyboard():
    """Doimiy reply keyboard — o'yinlar"""
    keyboard = [
        [KeyboardButton("🎯 Dart"), KeyboardButton("🎳 Bowling")],
        [KeyboardButton("⚽ Football"), KeyboardButton("🏀 Basketball")],
        [KeyboardButton("🎲 Dice"), KeyboardButton("🎰 Casino")],
        [KeyboardButton("🔙 Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True, one_time_keyboard=False)


# ============================================================
# GAME LOGIC
# ============================================================

EFFECTS = {
    "🎉": "5046509860389126442",
    "👍": "5107584321108051014",
    "👎": "5104858069142078462",
    "💩": "5046589136895476101",
}

GAME_EMOJIS = {
    "🎯 Dart": "🎯",
    "🎳 Bowling": "🎳",
    "⚽ Football": "⚽",
    "🏀 Basketball": "🏀",
    "🎲 Dice": "🎲",
    "🎰 Casino": "🎰",
}


def slot_combo(value: int) -> str:
    icons = ["🟥BAR", "🍇", "🍋", "7️⃣"]
    v = value - 1
    parts = []
    for _ in range(3):
        parts.append(icons[v % 4])
        v //= 4
    return " | ".join(parts)


def rate_result(emoji: str, value: int) -> str:
    if emoji in ("⚽", "🏀"):
        return "good" if value >= 4 else "none"
    if emoji in ("🎯", "🎳", "🎲"):
        if value == 6:
            return "good"
        if value >= 4:
            return "avg"
        if value >= 2:
            return "low"
        return "none"
    if emoji == "🎰":
        if value == 64:
            return "good"
        if value in (1, 22, 43):
            return "avg"
        return "low"
    return "low"


def effect_id_for_rating(rating: str) -> str:
    return EFFECTS.get({"good": "🎉", "avg": "👍", "low": "👎"}.get(rating, "💩"))


def result_text(emoji: str, value: int) -> str:
    if emoji == "⚽":
        return "⚽ GOOOL! ✅" if value >= 4 else "⚽ Gol bo'lmadi ❌"
    if emoji == "🏀":
        return "🏀 Savatga tushdi! ✅" if value >= 4 else "🏀 Tushmadi ❌"
    if emoji == "🎯":
        if value == 6:
            return "🎯 BULLSEYE! (markaz) ✅"
        if value == 1:
            return "🎯 Umuman tegmadi 💨"
        return f"🎯 Ochko: {value}"
    if emoji == "🎳":
        if value == 6:
            return "🎳 STRIKE! Hammasi yiqildi ✅"
        if value == 1:
            return "🎳 Hech narsa yiqilmadi 😬"
        return f"🎳 Qisman yiqildi (qiymat: {value})"
    if emoji == "🎲":
        return f"🎲 Son: {value}"
    if emoji == "🎰":
        combo = slot_combo(value)
        if value == 64:
            return f"🎰 JACKPOT! {combo} ✅"
        if value in (1, 22, 43):
            return f"🎰 3ta bir xil! {combo} ✅"
        return f"🎰 Tushganlari: {combo}"
    return f"{emoji} Natija: {value}"


# ============================================================
# AI LOGIC
# ============================================================

def get_reply(user_id, lang, user_text):
    key = f"{user_id}_{lang}"
    if key not in histories:
        histories[key] = [{"role": "system", "content": LANG_PROMPTS[lang]}]

    histories[key].append({"role": "user", "content": user_text})

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


# ============================================================
# HANDLERS
# ============================================================

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
    """Inline button — til tanlash"""
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

    # Til tanlanganida asosiy reply keyboard chiqadi
    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text="👇 Pastdagi tugmalardan foydalaning yoki savol yozing:",
        reply_markup=main_reply_keyboard()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if not message or not message.text:
        return

    user_id = update.effective_user.id
    text = message.text.strip()

    # ── Asosiy menyu tugmalari ─────────────────────────────
    if text == "🎮 O'yinlar":
        await message.reply_text(
            "🎮 O'yin tanlang:",
            reply_markup=games_reply_keyboard()
        )
        return

    if text in ("🌐 Til o'zgartirish", "/lan"):
        await message.reply_text(
            "Tilni tanlang / Выберите язык / Choose language:",
            reply_markup=lang_keyboard()
        )
        return

    if text == "🔙 Orqaga":
        await message.reply_text(
            "Asosiy menyuga qaytdingiz:",
            reply_markup=main_reply_keyboard()
        )
        return

    # ── O'yin tugmalari ────────────────────────────────────
    if text in GAME_EMOJIS:
        emoji = GAME_EMOJIS[text]
        dice_msg = await context.bot.send_dice(chat_id=message.chat.id, emoji=emoji)
        await asyncio.sleep(5)

        value = dice_msg.dice.value
        rating = rate_result(emoji, value)
        effect_id = effect_id_for_rating(rating) if message.chat.type == "private" else None

        await context.bot.send_message(
            chat_id=message.chat.id,
            text=result_text(emoji, value),
            reply_markup=games_reply_keyboard(),
            message_effect_id=effect_id,
        )
        return

    # ── AI chat ────────────────────────────────────────────
    if user_id not in user_langs:
        await message.reply_text(
            "Avval tilni tanlang / Сначала выберите язык / Please choose a language:",
            reply_markup=lang_keyboard()
        )
        return

    lang = user_langs[user_id]
    await context.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        answer = get_reply(user_id, lang, text)
    except Exception as e:
        answer = f"Xatolik: {e}"

    await message.reply_text(answer, reply_markup=main_reply_keyboard())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Xatolik: {context.error}")


# ============================================================
# MAIN
# ============================================================

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lan", lang_command))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=["message", "business_message", "callback_query"])


if __name__ == "__main__":
    main()
