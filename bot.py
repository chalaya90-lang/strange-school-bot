import asyncio
import os
import json
import random

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import gspread
from google.oauth2.service_account import Credentials

kyiv = pytz.timezone("Europe/Kyiv")

TOKEN = "8582009214:AAEwkSe7XPSvnt42rWQoJktYRmhQU3iwtfE"

ADMIN_NAMES = {"Марія Чала", "Лілія Шрам", "Чала Любов"}

# ================= ДАНІ =================

coins = {}
class_bank = 0
user_states = {}
user_names = {}
users = set()

active_modes = []
last_mode_date = None

wake_users = set()

# ================= ЗБЕРЕЖЕННЯ =================

def save_data():
    with open("data.json", "w") as f:
        json.dump({
            "coins": coins,
            "bank": class_bank
        }, f)

def load_data():
    global coins, class_bank
    try:
        with open("data.json") as f:
            data = json.load(f)
            coins = data.get("coins", {})
            class_bank = data.get("bank", 0)
    except:
        pass

# ================= GOOGLE =================

schedule_sheet = None
ideas_sheet = None

try:
    creds = Credentials.from_service_account_info(
        json.loads(os.getenv("GOOGLE_CREDENTIALS")),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    gc = gspread.authorize(creds)

    schedule_sheet = gc.open("Відсутність учнів").worksheet("Розклад")
    ideas_sheet = gc.open("Відсутність учнів").worksheet("Ідеї")

    print("GOOGLE OK ✅")

except Exception as e:
    print("GOOGLE ERROR ❌", e)

# ================= BOT =================

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# ================= КНОПКИ =================

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💡 Ідеї для класу")],
        [KeyboardButton(text="😂 Мем дня"), KeyboardButton(text="🎯 Челендж дня")],
        [KeyboardButton(text="💌 Написати добро"), KeyboardButton(text="🎰 Удача")],
        [KeyboardButton(text="😴 Я прокинувся")],
        [KeyboardButton(text="🪙 Мої монетки"), KeyboardButton(text="🏦 Банк класу")],
        [KeyboardButton(text="🏆 Рейтинг"), KeyboardButton(text="⚖️ Дія вчителя")]
    ],
    resize_keyboard=True
)

# ================= МОНЕТКИ =================

def add_coins(uid, amount):
    coins[str(uid)] = coins.get(str(uid), 0) + amount
    save_data()

def remove_coins(uid, amount):
    coins[str(uid)] = max(0, coins.get(str(uid), 0) - amount)
    save_data()

# ================= РЕЖИМИ =================

game_modes = ["мем","челендж","добро","лотерея"]

def generate_modes():
    global active_modes, last_mode_date

    today = datetime.now(kyiv).date()

    if str(today) == str(last_mode_date):
        return

    active_modes = random.sample(game_modes, 2)
    last_mode_date = today

def is_active(mode):
    return mode in active_modes

# ================= HANDLER =================

@router.message()
async def handler(msg: types.Message):

    global class_bank

    uid = msg.chat.id
    text = msg.text or ""

    users.add(uid)
    user_names[uid] = user_names.get(uid, f"User_{uid}")

    # 🔥 START
    if text == "/start":
        await msg.answer(
            "Я живий 😎\nОбирай кнопку👇",
            reply_markup=main_kb
        )
        return

    # базова монетка
    add_coins(uid, 1)

    # ===== ІДЕЇ =====
    if text == "💡 Ідеї для класу":
        user_states[uid] = "idea"
        await msg.answer("Напиши ідею")
        return

    if user_states.get(uid) == "idea":

        if ideas_sheet:
            ideas_sheet.append_row([
                datetime.now(kyiv).strftime("%d.%m %H:%M"),
                user_names.get(uid,"???"),
                text
            ])

        add_coins(uid, 5)
        user_states.pop(uid, None)

        await msg.answer("🔥 +5 монеток")
        return

    # ===== МЕМ =====
    if text == "😂 Мем дня":

        if not is_active("мем"):
            await msg.answer("Сьогодні без мемів")
            return

        user_states[uid] = "meme"
        await msg.answer("Скинь мем")
        return

    if user_states.get(uid) == "meme":
        add_coins(uid, 5)
        user_states.pop(uid, None)
        await msg.answer("😂 +5")
        return

    # ===== ДОБРО =====
    if text == "💌 Написати добро":

        if not is_active("добро"):
            await msg.answer("Сьогодні без добра")
            return

        if not user_names:
            await msg.answer("Немає користувачів")
            return

        user_states[uid] = "good"
        await msg.answer("Напиши повідомлення")
        return

    if user_states.get(uid) == "good":

        target = random.choice(list(user_names.keys()))

        await bot.send_message(target, f"💌 Хтось написав:\n{text}")

        add_coins(uid, 3)
        user_states.pop(uid, None)

        await msg.answer("+3 🪙")
        return

    # ===== ЛОТЕРЕЯ =====
    if text == "🎰 Удача":

        if not is_active("лотерея"):
            await msg.answer("Сьогодні не граємо")
            return

        reward = random.choice([0,0,5,10])
        add_coins(uid, reward)

        await msg.answer(f"{reward} 🪙")
        return

    # ===== ПРОКИНУВСЯ =====
    if text == "😴 Я прокинувся":

        if uid not in wake_users:
            wake_users.add(uid)
            add_coins(uid, 3)
            await msg.answer("☀️ +3")
        else:
            await msg.answer("Вже прокинувся 😄")
        return

    # ===== МОНЕТКИ =====
    if text == "🪙 Мої монетки":
        await msg.answer(f"{coins.get(str(uid),0)} 🪙")
        return

    if text == "🏦 Банк класу":
        await msg.answer(f"{class_bank} 🪙")
        return

    # ===== РЕЙТИНГ =====
    if text == "🏆 Рейтинг":

        r = sorted(coins.items(), key=lambda x: x[1], reverse=True)

        txt = "🏆 ТОП\n"

        for i,(u,c) in enumerate(r[:5],1):
            name = user_names.get(int(u),"???")
            txt += f"{i}. {name} — {c}\n"

        await msg.answer(txt)
        return

    # ===== ШТРАФИ =====
    if text == "⚖️ Дія вчителя":

        if user_names.get(uid) not in ADMIN_NAMES:
            await msg.answer("Тільки для вчителя")
            return

        user_states[uid] = "teacher"

        await msg.answer(
            "1 Мінус учню\n"
            "2 Мінус класу\n"
            "3 Штраф-жарт\n"
            "4 Допомога\n"
            "5 Амністія"
        )
        return

# ================= MAIN =================

async def main():

    load_data()

    await bot.delete_webhook(drop_pending_updates=True)

    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
