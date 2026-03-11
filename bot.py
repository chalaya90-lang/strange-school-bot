import asyncio
import os
import json

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

import gspread
from google.oauth2.service_account import Credentials


kyiv = pytz.timezone("Europe/Kyiv")


TOKEN = "8582009214:AAEwkSe7XPSvnt42rWQoJktYRmhQU3iwtfE"

ADMIN_NAMES = {"Марія Чала", "Лілія Шрам"}


# ---------------- GOOGLE SHEETS ----------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
gc = gspread.authorize(creds)

sheet = gc.open("Відсутність учнів").sheet1
schedule_sheet = gc.open("Відсутність учнів").worksheet("Розклад")


# ---------------- BOT ----------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

users = set()
user_names = {}
user_states = {}
usage_stats = {}


# ---------------- КЛАВІАТУРА ----------------

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Розклад")],
        [KeyboardButton(text="⏰ Який урок зараз?")],
        [KeyboardButton(text="📩 Повідомити про відсутність")],
        [KeyboardButton(text="📢 Оголошення")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🏆 Рейтинг активності")]
    ],
    resize_keyboard=True
)

back_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅ Назад")]],
    resize_keyboard=True
)


# ---------------- СТАТИСТИКА ----------------

def update_usage(user_id, action):

    if user_id not in usage_stats:
        usage_stats[user_id] = {"schedule": 0, "current": 0}

    usage_stats[user_id][action] += 1


# ---------------- ФАЙЛИ ----------------

def load_students():

    try:
        with open("students.txt", "r", encoding="utf-8") as f:

            for line in f:
                uid, name = line.strip().split("|")
                user_names[int(uid)] = name

    except:
        pass


def save_student(user_id, name):

    with open("students.txt", "a", encoding="utf-8") as f:
        f.write(f"{user_id}|{name}\n")


def save_absence(name, reason):

    now = datetime.now(kyiv).strftime("%d.%m.%Y %H:%M")

    with open("absences.txt", "a", encoding="utf-8") as f:
        f.write(f"{now} | {name} | {reason}\n")

    sheet.append_row([now, name, reason])


# ---------------- УРОК ЗАРАЗ ----------------

def get_current_lesson():

    rows = schedule_sheet.get_all_records()

    now = datetime.now(kyiv).time()
    today = (datetime.utcnow().hour + 3 >= 0) and datetime.utcnow().weekday()

    for row in rows:

        try:
            day = int(row["День"])
        except:
            continue

        if day != today:
            continue

        start = row["Початок"]
        end = row["Кінець"]
        subject = row["Предмет"]

        start_t = datetime.strptime(start, "%H:%M").time()
        end_t = datetime.strptime(end, "%H:%M").time()

        if start_t <= now <= end_t:
            return start, end, subject

    return None


# ---------------- СЬОГОДНІШНІЙ РОЗКЛАД ----------------

def get_today_schedule():

    rows = schedule_sheet.get_all_records()
    today = datetime.now(kyiv).weekday()

    lessons = []

    for row in rows:

        try:
            day = int(row["День"])
        except:
            continue

        if day != today:
            continue

        lessons.append(row)

    lessons.sort(key=lambda x: x["Початок"])

    return lessons


# ---------------- HANDLER ----------------

@dp.message()
async def handler(message: types.Message):

    text = message.text
    user_id = message.chat.id

    users.add(user_id)

    state = user_states.get(user_id)


    # ---------- START ----------

    if text == "/start":

        if user_id not in user_names:

            user_states[user_id] = "waiting_name"
            await message.answer("Введіть прізвище та ім’я ✍️")
            return

        await message.answer("Головне меню 📚", reply_markup=main_kb)
        return


    # ---------- ІМ'Я ----------

    if state == "waiting_name":

        name = text.strip()

        if len(name.split()) < 2:
            await message.answer("Введіть прізвище та ім’я")
            return

        user_names[user_id] = name
        save_student(user_id, name)

        await message.answer("Збережено ✅", reply_markup=main_kb)
        return


    # ---------- РОЗКЛАД ----------

    if text == "📅 Розклад":

        update_usage(user_id, "schedule")

        lessons = get_today_schedule()

        if not lessons:
            await message.answer("Сьогодні уроків немає 😎")
            return

        text_lessons = ""

        for row in lessons:

            start = row["Початок"]
            end = row["Кінець"]
            subject = row["Предмет"]

            text_lessons += f"{subject} ({start}-{end})\n"

        await message.answer(f"📚 Сьогодні:\n\n{text_lessons}")

        return


    # ---------- ЯКИЙ УРОК ----------

    if text == "⏰ Який урок зараз?":

        update_usage(user_id, "current")

        lesson = get_current_lesson()

        if lesson:

            start, end, subject = lesson

            await message.answer(
                f"📖 Зараз урок\n{subject}\n{start}-{end}"
            )

        else:

            await message.answer("⏳ Зараз перерва")

        return


    # ---------- ВІДСУТНІСТЬ ----------

    if text == "📩 Повідомити про відсутність":

        user_states[user_id] = "waiting_absence"

        await message.answer("Напишіть причину ✍️", reply_markup=back_kb)

        return


    if state == "waiting_absence":

        name = user_names.get(user_id, "Невідомий")

        save_absence(name, text)

        await message.answer("Запис додано ✅", reply_markup=main_kb)

        return


    # ---------- ОГОЛОШЕННЯ ----------

    if text == "📢 Оголошення":

        name = user_names.get(user_id)

        if name not in ADMIN_NAMES:
            await message.answer("Доступ тільки для адміністрації 🔒")
            return

        user_states[user_id] = "waiting_announcement"

        await message.answer("Напишіть оголошення")

        return


    if state == "waiting_announcement":

        for u in users:

            try:
                await bot.send_message(u, f"📢 ОГОЛОШЕННЯ\n\n{text}")
            except:
                pass

        await message.answer("Оголошення розіслано")

        return


    # ---------- СТАТИСТИКА ----------

    if text == "📊 Статистика":

        name = user_names.get(user_id)

        if name not in ADMIN_NAMES:
            await message.answer("Доступ тільки для адміністрації 🔒")
            return

        today = datetime.now(kyiv)).strftime("%d.%m.%Y")

        count = 0

        try:
            with open("absences.txt", "r", encoding="utf-8") as f:

                for line in f:

                    if today in line:
                        count += 1

        except:
            pass

        await message.answer(f"📊 Відсутніх сьогодні: {count}")

        return


    # ---------- РЕЙТИНГ ----------

    if text == "🏆 Рейтинг активності":

        ranking = []

        for uid, stats in usage_stats.items():

            total = stats["schedule"] + stats["current"]

            name = user_names.get(uid, "Невідомий")

            ranking.append((name, total))

        ranking.sort(key=lambda x: x[1], reverse=True)

        result = "🏆 Рейтинг активності\n\n"

        for i, (name, total) in enumerate(ranking[:5], start=1):
            result += f"{i}. {name} — {total}\n"

        await message.answer(result)

        return


# ---------------- MAIN ----------------

async def main():

    load_students()

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())

