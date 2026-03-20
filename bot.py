import asyncio
import os
import json
import random
import re

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

import gspread
from google.oauth2.service_account import Credentials

kyiv = pytz.timezone("Europe/Kyiv")

TOKEN = "8582009214:AAEwkSe7XPSvnt42rWQoJktYRmhQU3iwtfE"

ADMIN_NAMES = {"Марія Чала", "Лілія Шрам", "Чала Любов"}
print("БОТ ЗАПУСТИВСЯ 🚀")
print("ПРИЙШЛО:", msg.text)

# ================= ДАНІ =================

coins = {}
class_bank = 0

active_modes = []
last_mode_date = None

wake_users = set()
user_states = {}
user_names = {}
users = set()

# ================= ЗБЕРЕЖЕННЯ =================

def save_data():
    with open("data.json", "w") as f:
        json.dump({
            "coins": coins,
            "bank": class_bank,
            "modes": active_modes,
            "date": str(last_mode_date)
        }, f)

def load_data():
    global coins, class_bank, active_modes

    try:
        with open("data.json") as f:
            data = json.load(f)
            coins = data.get("coins", {})
            class_bank = data.get("bank", 0)
            active_modes = data.get("modes", [])
    except:
        pass

# ================= СТУДЕНТИ =================

def load_students():
    try:
        with open("students.txt", "r", encoding="utf-8") as f:
            for line in f:
                uid, name = line.strip().split("|")
                user_names[int(uid)] = name
    except:
        pass

def save_student(uid, name):
    with open("students.txt", "a", encoding="utf-8") as f:
        f.write(f"{uid}|{name}\n")

# ================= GOOGLE =================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    json.loads(os.getenv("GOOGLE_CREDENTIALS")),
    scopes=SCOPES
)

gc = gspread.authorize(creds)

sheet = gc.open("Відсутність учнів").sheet1
schedule_sheet = gc.open("Відсутність учнів").worksheet("Розклад")
ideas_sheet = gc.open("Відсутність учнів").worksheet("Ідеї")

# ================= BOT =================

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= КНОПКИ =================

main_kb = ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text="📅 Розклад")],
[KeyboardButton(text="⏰ Який урок зараз?")],
[KeyboardButton(text="🔔 Дзвінки")],
[KeyboardButton(text="💡 Ідеї для класу")],
[KeyboardButton(text="😂 Мем дня"), KeyboardButton(text="🎯 Челендж дня")],
[KeyboardButton(text="💌 Написати добро"), KeyboardButton(text="🎰 Удача")],
[KeyboardButton(text="😴 Я прокинувся"), KeyboardButton(text="🪙 Мої монетки")],
[KeyboardButton(text="🏦 Банк класу"), KeyboardButton(text="🎁 Магазин")],
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
    save_data()

def is_active(mode):
    return mode in active_modes

# ================= БУДИЛЬНИК =================

async def alarm():
    last_day = None

    while True:

        now = datetime.now(kyiv)

        if now.hour == 7 and 45 <= now.minute <= 46 and last_day != now.date():

            generate_modes()

            text = "☀️ Доброго ранку\n\n"

            for r in schedule_sheet.get_all_records():
                if int(r["День"]) == now.weekday():
                    text += f"{r['Предмет']} ({r['Початок']}-{r['Кінець']})\n"

            text += "\n🎮 Сьогодні активні:\n"

            names = {
                "мем":"😂 Мем дня",
                "челендж":"🎯 Челендж",
                "добро":"💌 Добро",
                "лотерея":"🎰 Лотерея"
            }

            for m in active_modes:
                text += f"• {names[m]}\n"

            for u in users:
                try:
                    await bot.send_voice(
                        u,
                        voice=FSInputFile("alarm.mp3.mp3"),
                        caption=text
                    )
                except:
                    pass

            last_day = now.date()

        await asyncio.sleep(20)

# ================= HANDLER =================

@dp.message()
async def handler(msg: types.Message):

    global class_bank

    uid = msg.chat.id
    text = msg.text

    users.add(uid)

    # базова монетка
    add_coins(uid, 1)

    # ===== ІДЕЇ =====
    if text == "💡 Ідеї для класу":
        user_states[uid] = "idea"
        await msg.answer("Напиши ідею")
        return

    if user_states.get(uid) == "idea":
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

    if user_states.get(uid) == "teacher":

        if text == "1":
            user_states[uid] = "penalty_user"
            await msg.answer("Введи ПІБ")
            return

        if text == "2":
            class_bank = max(0, class_bank - 5)
            save_data()
            await msg.answer("🧨 -5 класу")
            return

        if text == "3":
            await msg.answer("🤝 Скажи комплімент класу")
            return

        if text == "4":
            user_states[uid] = "reward_user"
            await msg.answer("Хто допоміг?")
            return

        if text == "5":
            for u in user_names.keys():
                add_coins(u, 3)
            await msg.answer("🧼 +3 всім")
            return

    if user_states.get(uid) == "penalty_user":

        target = None

        for u,n in user_names.items():
            if n == text:
                target = u

        if not target:
            await msg.answer("Не знайдено")
            return

        user_states[uid] = ("penalty_amount", target)

        await msg.answer("Скільки? (1/3/5)")
        return

    if isinstance(user_states.get(uid), tuple):

        state, target = user_states[uid]

        if state == "penalty_amount":

            if not text.isdigit():
                await msg.answer("Введи число")
                return

            remove_coins(target, int(text))

            await bot.send_message(
                target,
                f"⚠️ -{text} 🪙\nСьогодні не твій день 😄"
            )

            user_states.pop(uid, None)
            await msg.answer("Готово")
            return

    if user_states.get(uid) == "reward_user":

        for u,n in user_names.items():
            if n == text:
                add_coins(u, 2)
                user_states.pop(uid, None)
                await msg.answer("+2 🪙")
                return

# ================= MAIN =================

async def main():

    load_data()
    load_students()

    await bot.delete_webhook(drop_pending_updates=True)
    
    asyncio.create_task(alarm())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
