import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from openai import OpenAI

# ============================================================
# TOKENS & KEYS
# ============================================================

TELEGRAM_BOT_TOKEN = "8342079117:AAEm6pYd5FMnNqFkGIlCrHh3epfkU8bOJ1s"

client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

bot = Bot(TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ============================================================
# KEYBOARDS
# ============================================================

# Doimiy rangli o'yin tugmalari (asl koddan o'zgarishsiz)
GAMES_KB = {
    "keyboard": [
        [{"text": "🎯 Dart"}, {"text": "🎳 Bowling"}],
        [{"text": "⚽ Football"}, {"text": "🏀 Basketball"}],
        [{"text": "🎲 Dice"}, {"text": "🎰 Casino"}],
        [{"text": "🔙 Orqaga"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
    "one_time_keyboard": False,
}

# Asosiy menyu
MAIN_KB = {
    "keyboard": [
        [{"text": "🎮 O'yinlar"}, {"text": "🌐 Til o'zgartirish"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
    "one_time_keyboard": False,
}

def lang_inline_kb():
    keyboard = [[
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ============================================================
# AI CONFIG
# ============================================================

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

def get_ai_reply(user_id, lang, user_text):
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
# GAME LOGIC (asl koddan o'zgarishsiz)
# ============================================================

EFFECTS = {
    "🎉": "5046509860389126442",
    "👍": "5107584321108051014",
    "👎": "5104858069142078462",
    "💩": "5046589136895476101",
}

GAME_MAPPING = {
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
    if emoji == "🎯":
        if value == 6: return "good"
        if value >= 4: return "avg"
        if value >= 2: return "low"
        return "none"
    if emoji == "🎳":
        if value == 6: return "good"
        if value >= 4: return "avg"
        if value >= 2: return "low"
        return "none"
    if emoji == "🎲":
        if value == 6: return "good"
        if value >= 4: return "avg"
        if value >= 2: return "low"
        return "none"
    if emoji == "🎰":
        if value == 64: return "good"
        if value in (1, 22, 43): return "avg"
        return "low"
    return "low"

def effect_id_for_rating(rating: str) -> str:
    if rating == "good": return EFFECTS["🎉"]
    if rating == "avg":  return EFFECTS["👍"]
    if rating == "low":  return EFFECTS["👎"]
    return EFFECTS["💩"]

def result_text(emoji: str, value: int) -> str:
    if emoji == "⚽":
        return "⚽ GOOOL! ✅" if value >= 4 else "⚽ Gol bo'lmadi ❌"
    if emoji == "🏀":
        return "🏀 Savatga tushdi! ✅" if value >= 4 else "🏀 Tushmadi ❌"
    if emoji == "🎯":
        if value == 6: return "🎯 BULLSEYE! (markaz) ✅"
        if value == 1: return "🎯 Umuman tegmadi 💨"
        return f"🎯 Ochko: {value}"
    if emoji == "🎳":
        if value == 6: return "🎳 STRIKE! Hammasi yiqildi ✅"
        if value == 1: return "🎳 Hech narsa yiqilmadi 😬"
        return f"🎳 Qisman yiqildi (qiymat: {value})"
    if emoji == "🎲":
        return f"🎲 Son: {value}"
    if emoji == "🎰":
        combo = slot_combo(value)
        if value == 64: return f"🎰 JACKPOT! {combo} ✅"
        if value in (1, 22, 43): return f"🎰 3ta bir xil! {combo} ✅"
        return f"🎰 Tushganlari: {combo}"
    return f"{emoji} Natija: {value}"

# ============================================================
# HANDLERS
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Tilni tanlang / Выберите язык / Choose language:",
        reply_markup=lang_inline_kb()
    )

@dp.message(Command("lan"))
async def lang_command(message: Message):
    await message.answer(
        "Tilni tanlang / Выберите язык / Choose language:",
        reply_markup=lang_inline_kb()
    )

@dp.callback_query(F.data.startswith("lang_"))
async def lang_callback(callback: CallbackQuery):
    lang = callback.data.replace("lang_", "")
    user_id = callback.from_user.id
    user_langs[user_id] = lang
    messages = {
        "uz": "✅ Til o'rnatildi: O'zbek 🇺🇿",
        "ru": "✅ Язык установлен: Русский 🇷🇺",
        "en": "✅ Language set: English 🇬🇧",
    }
    await callback.message.edit_text(messages[lang])
    await callback.message.answer(
        "👇 Pastdagi tugmalardan foydalaning yoki savol yozing:",
        reply_markup=MAIN_KB
    )
    await callback.answer()

@dp.message(F.text == "🎮 O'yinlar")
async def games_menu(message: Message):
    await message.answer("🎮 O'yin tanlang:", reply_markup=GAMES_KB)

@dp.message(F.text == "🌐 Til o'zgartirish")
async def change_lang(message: Message):
    await message.answer(
        "Tilni tanlang / Выберите язык / Choose language:",
        reply_markup=lang_inline_kb()
    )

@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: Message):
    await message.answer("Asosiy menyu:", reply_markup=MAIN_KB)

@dp.message(F.text.in_(GAME_MAPPING.keys()))
async def play_game(message: Message):
    emoji = GAME_MAPPING[message.text]
    dice_msg = await bot.send_dice(chat_id=message.chat.id, emoji=emoji)
    await asyncio.sleep(5)
    value = dice_msg.dice.value
    rating = rate_result(emoji, value)
    effect_id = effect_id_for_rating(rating) if message.chat.type == "private" else None
    await bot.send_message(
        chat_id=message.chat.id,
        text=result_text(emoji, value),
        reply_markup=GAMES_KB,
        message_effect_id=effect_id,
    )

@dp.message(F.text)
async def ai_chat(message: Message):
    user_id = message.from_user.id
    if user_id not in user_langs:
        await message.answer(
            "Avval tilni tanlang / Сначала выберите язык / Please choose a language:",
            reply_markup=lang_inline_kb()
        )
        return
    lang = user_langs[user_id]
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        answer = get_ai_reply(user_id, lang, message.text)
    except Exception as e:
        answer = f"Xatolik: {e}"
    await message.answer(answer, reply_markup=MAIN_KB)

# ============================================================
# MAIN
# ============================================================

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
