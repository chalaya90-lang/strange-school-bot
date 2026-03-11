import asyncio
import os
import json
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

import gspread
from google.oauth2.service_account import Credentials


TOKEN = "8582009214:AAEwkSe7XPSvnt42rWQoJktYRmhQU3iwtfE"

ADMIN_IDS = {
    5687913918,       # Марія Чала
    123456789    # Лілія Шрам
}


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


def load_schedule():

    rows = schedule_sheet.get_all_records()

    schedule = {}

    for row in rows:

        if not row["День"] or not row["Урок"]:
            continue

        day = int(row["День"])
        lesson = int(row["Урок"])
        subject = row["Предмет"]

        if day not in schedule:
            schedule[day] = []

        schedule[day].append((lesson, subject))

    return schedule


# ------------------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

schedule = {}

user_states = {}
user_names = {}
users = set()
usage_stats = {}


# ---------------- СКОРОЧЕНІ ДЗВІНКИ ----------------
lesson_times = {
    1: ("08:00","08:35"),
    2: ("08:40","09:15"),
    3: ("09:20","09:55"),
    4: ("10:00","10:35"),
    5: ("10:40","11:15"),
    6: ("11:30","12:05"),
    7: ("12:10","12:45"),
    8: ("12:50","13:25"),
    9: ("14:00","14:45"),
    10: ("15:40","16:25"),
    11: ("16:30","17:15")
}


# ---------------- КЛАВІАТУРА ----------------
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Розклад")],
        [KeyboardButton(text="⏰ Який урок зараз?")],
        [KeyboardButton(text="🔔 Дзвінки")],
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

    except FileNotFoundError:
        pass


def save_student(user_id, name):

    with open("students.txt", "a", encoding="utf-8") as f:
        f.write(f"{user_id}|{name}\n")


def save_absence(name, reason):

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    with open("absences.txt", "a", encoding="utf-8") as f:
        f.write(f"{now} | {name} | {reason}\n")

    sheet.append_row([now, name, reason])


# ---------------- РАНКОВЕ ПОВІДОМЛЕННЯ ----------------
async def morning_message():

    sent_today = False

    while True:

        now = datetime.now()

        if now.hour == 7 and now.minute == 45 and not sent_today:

            today = now.weekday()

            if today in schedule:

                lessons = sorted(schedule[today], key=lambda x: x[0])

                if lessons:

                    first_lesson = lessons[0][0]
                    first_time = lesson_times[first_lesson][0]

                    text = (
                        f"Доброго ранку ☀️\n"
                        f"Сьогодні {len(lessons)} уроків\n"
                        f"Перший о {first_time}"
                    )

                    audio = FSInputFile("alarm.mp3")

                    for user_id in users:

                        try:
                            await bot.send_message(user_id, text)
                            await bot.send_audio(user_id, audio)

                        except:
                            pass

                    sent_today = True

        if now.hour == 8:
            sent_today = False

        await asyncio.sleep(30)


# ---------------- HANDLER ----------------
@dp.message()
async def handler(message: types.Message):

    text = message.text
    user_id = message.chat.id
    users.add(user_id)

    state = user_states.get(user_id)

    # ---- START ----
    if text == "/start":

        if user_id not in user_names:
            user_states[user_id] = "waiting_name"
            await message.answer("Введіть прізвище та ім’я ✍️")
            return

        await message.answer("Головне меню 📚", reply_markup=main_kb)
        return

    # ---- НАЗАД ----
    if text == "⬅ Назад":

        user_states[user_id] = "menu"
        await message.answer("Головне меню 📚", reply_markup=main_kb)
        return

    # ---- ВВЕДЕННЯ ІМЕНІ ----
    if state == "waiting_name":

        name = text.strip()
        parts = name.split()

        if len(parts) < 2:
            await message.answer("🤭 Потрібне прізвище та ім’я.")
            return

        if not all(part.replace("'", "").isalpha() for part in parts):
            await message.answer("😑 Без цифр і символів.")
            return

        user_names[user_id] = name
        save_student(user_id, name)

        user_states[user_id] = "menu"

        await message.answer(f"Збережено як: {name} ✅", reply_markup=main_kb)

        return

    # ---- РОЗКЛАД ----
    if text == "📅 Розклад":

        update_usage(user_id, "schedule")

        today = datetime.now().weekday()

        if today not in schedule:
            await message.answer("Сьогодні уроків немає 😎")
            return

        lessons = sorted(schedule[today], key=lambda x: x[0])

        lessons_text = ""

        for lesson in lessons:

            lesson_number = lesson[0]
            subject = lesson[1]

            if lesson_number in lesson_times:

                start, end = lesson_times[lesson_number]

                lessons_text += f"{lesson_number}. {subject} ({start}-{end})\n"

        first_num = lessons[0][0]
        last_num = lessons[-1][0]

        first_start = lesson_times[first_num][0]
        last_end = lesson_times[last_num][1]

        await message.answer(
            f"📚 Сьогодні {len(lessons)} уроків\n"
            f"Перший урок: {first_start}\n"
            f"Останній урок: {last_end}\n\n"
            f"{lessons_text}"
        )

        return

    # ---- ЯКИЙ УРОК ----
    if text == "⏰ Який урок зараз?":

        update_usage(user_id, "current")

        now = datetime.now().time()
        today = datetime.now().weekday()

        if today not in schedule:
            await message.answer("Уроків немає 😌")
            return

        for lesson_number, lesson in schedule[today]:

            start, end = lesson_times[lesson_number]

            start_t = datetime.strptime(start, "%H:%M").time()
            end_t = datetime.strptime(end, "%H:%M").time()

            if start_t <= now <= end_t:

                await message.answer(
                    f"Зараз {lesson_number} урок 📖\n"
                    f"{lesson}\n"
                    f"{start}-{end}"
                )

                return

        await message.answer("Зараз перерва 😎")

        return

    # ---- ДЗВІНКИ ----
    if text == "🔔 Дзвінки":

        times = ""

        for num, (start, end) in lesson_times.items():
            times += f"{num}. {start}-{end}\n"

        await message.answer(f"🔔 Скорочені дзвінки:\n\n{times}")

        return

    # ---- ВІДСУТНІСТЬ ----
    if text == "📩 Повідомити про відсутність":

        user_states[user_id] = "waiting_absence"

        await message.answer("Напишіть причину ✍️", reply_markup=back_kb)

        return

    if state == "waiting_absence":

        name = user_names.get(user_id, "Невідомий")

        save_absence(name, text)

        user_states[user_id] = "menu"

        await message.answer("Запис додано в журнал ✅", reply_markup=main_kb)

        return


# ---------------- ЗАПУСК ----------------
async def main():

    global schedule

    load_students()

    schedule = load_schedule()

    asyncio.create_task(morning_message())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

