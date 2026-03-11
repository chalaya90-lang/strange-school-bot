import asyncio
import os
import json
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

import gspread
from google.oauth2.service_account import Credentials


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


# ---------------- ДЗВІНКИ ----------------

lesson_times = {

    1: ("08:00", "08:35"),
    2: ("08:40", "09:15"),
    3: ("09:20", "09:55"),
    4: ("10:00", "10:35"),
    5: ("10:40", "11:15"),
    6: ("11:30", "12:05"),
    7: ("12:10", "12:45"),
    8: ("12:50", "13:25"),
    9: ("13:30", "14:05"),
    10: ("14:10", "14:45"),
    11: ("14:50", "15:25")

}


# ---------------- LOAD SCHEDULE ----------------

def load_schedule():

    rows = schedule_sheet.get_all_records()

    schedule = {}

    for row in rows:

        try:

            day = int(row["День"])
            lesson = int(row["Урок"])
            subject = str(row["Предмет"]).strip()

        except:
            continue

        if subject == "":
            continue

        if lesson not in lesson_times:
            continue

        if day not in schedule:
            schedule[day] = []

        schedule[day].append((lesson, subject))

    for day in schedule:
        schedule[day] = sorted(schedule[day], key=lambda x: x[0])

    return schedule


# ---------------- BOT ----------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

schedule = {}

users = set()
user_names = {}
user_states = {}

usage_stats = {}


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


# ---------------- СТУДЕНТИ ----------------

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


# ---------------- ВІДСУТНІСТЬ ----------------

def save_absence(name, reason):

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    with open("absences.txt", "a", encoding="utf-8") as f:
        f.write(f"{now} | {name} | {reason}\n")

    sheet.append_row([now, name, reason])


# ---------------- УРОК ЗАРАЗ ----------------

def get_current_lesson(today):

    global schedule
    schedule = load_schedule()

    if today not in schedule:
        return None

    now = datetime.now().time()

    for lesson_number, subject in schedule[today]:

        start, end = lesson_times[lesson_number]

        start_t = datetime.strptime(start, "%H:%M").time()
        end_t = datetime.strptime(end, "%H:%M").time()

        if start_t <= now <= end_t:
            return lesson_number, subject, start, end

    return None


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

    # ---- ІМ'Я ----

    if state == "waiting_name":

        name = text.strip()

        if len(name.split()) < 2:
            await message.answer("Введіть прізвище та ім’я")
            return

        user_names[user_id] = name
        save_student(user_id, name)

        await message.answer("Збережено ✅", reply_markup=main_kb)
        return

    # ---- РОЗКЛАД ----

    if text == "📅 Розклад":

        update_usage(user_id, "schedule")

        global schedule
        schedule = load_schedule()

        today = datetime.now().weekday()

        if today not in schedule:

            await message.answer("Сьогодні уроків немає 😎")
            return

        lessons = schedule[today]

        txt = ""

        for lesson_number, subject in lessons:

            start, end = lesson_times[lesson_number]

            txt += f"{lesson_number}. {subject} ({start}-{end})\n"

        first = lessons[0][0]
        last = lessons[-1][0]

        await message.answer(

            f"📚 Сьогодні {len(lessons)} уроків\n"
            f"Перший: {lesson_times[first][0]}\n"
            f"Останній: {lesson_times[last][1]}\n\n"
            f"{txt}"
        )

        return

    # ---- ЯКИЙ УРОК ----

    if text == "⏰ Який урок зараз?":

        update_usage(user_id, "current")

        today = datetime.now().weekday()

        lesson = get_current_lesson(today)

        if lesson:

            num, subject, start, end = lesson

            await message.answer(
                f"📖 Зараз {num} урок\n{subject}\n{start}-{end}"
            )

        else:

            await message.answer("⏳ Зараз перерва")

        return

    # ---- ДЗВІНКИ ----

    if text == "🔔 Дзвінки":

        txt = ""

        for num, (start, end) in lesson_times.items():
            txt += f"{num}. {start}-{end}\n"

        await message.answer(f"🔔 Скорочені дзвінки\n\n{txt}")

        return

    # ---- ВІДСУТНІСТЬ ----

    if text == "📩 Повідомити про відсутність":

        user_states[user_id] = "waiting_absence"

        await message.answer("Напишіть причину ✍️", reply_markup=back_kb)

        return

    if state == "waiting_absence":

        name = user_names.get(user_id, "Невідомий")

        save_absence(name, text)

        await message.answer("Запис додано ✅", reply_markup=main_kb)

        return

    # ---- ОГОЛОШЕННЯ ----

    if text == "📢 Оголошення":

        name = user_names.get(user_id)

        if name not in ADMIN_NAMES:
            await message.answer("Доступ тільки для адміністрації 🔒")
            return

        user_states[user_id] = "waiting_announcement"

        await message.answer("Напишіть оголошення 📝")

        return

    if state == "waiting_announcement":

        for u in users:

            try:
                await bot.send_message(u, f"📢 ОГОЛОШЕННЯ\n\n{text}")
            except:
                pass

        await message.answer("Оголошення розіслано ✅")

        return


# ---------------- БУДИЛЬНИК ----------------

async def morning_alarm():

    while True:

        global schedule
        schedule = load_schedule()

        now = datetime.now()

        if now.hour == 7 and now.minute == 45:

            today = now.weekday()

            if today in schedule:

                lessons = schedule[today]

                first = lessons[0][0]

                start = lesson_times[first][0]

                text = (
                    "☀️ Доброго ранку\n"
                    f"Сьогодні {len(lessons)} уроків\n"
                    f"Перший о {start}"
                )

                for user in users:

                    try:
                        await bot.send_audio(
                            user,
                            audio=FSInputFile("alarm.mp3"),
                            caption=text
                        )
                    except:
                        pass

        await asyncio.sleep(60)


# ---------------- АВТО ДЗВІНКИ ----------------

async def lesson_notifications():

    last_lesson = None

    while True:

        global schedule
        schedule = load_schedule()

        now = datetime.now()
        today = now.weekday()

        if today in schedule:

            for lesson_number, subject in schedule[today]:

                start, end = lesson_times[lesson_number]

                start_t = datetime.strptime(start, "%H:%M").time()

                if now.hour == start_t.hour and now.minute == start_t.minute:

                    if last_lesson != lesson_number:

                        text = (
                            f"🔔 Почався {lesson_number} урок\n"
                            f"{subject}\n"
                            f"{start}-{end}"
                        )

                        for user in users:

                            try:
                                await bot.send_message(user, text)
                            except:
                                pass

                        last_lesson = lesson_number

        await asyncio.sleep(30)


# ---------------- MAIN ----------------

async def main():
    print("РОЗКЛАД:", schedule)

    global schedule

    load_students()

    schedule = load_schedule()

    asyncio.create_task(morning_alarm())
    asyncio.create_task(lesson_notifications())

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())

