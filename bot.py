import asyncio
import os
import json
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import gspread
from google.oauth2.service_account import Credentials


TOKEN = "8582009214:AAEwkSe7XPSvnt42rWQoJktYRmhQU3iwtfE"
ADMIN_IDS = {123456789, 5687913918}

# ---------------- GOOGLE SHEETS ----------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open("Відсутність учнів").sheet1
# ------------------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_states = {}
user_names = {}
users = set()
usage_stats = {}

# ---------------- СТАТИСТИКА ----------------
def update_usage(user_id, action):
    if user_id not in usage_stats:
        usage_stats[user_id] = {"schedule": 0, "current": 0}
    usage_stats[user_id][action] += 1


# ---------------- РОЗКЛАД ----------------
lesson_times = [
    ("08:00", "08:35"),
    ("08:40", "09:15"),
    ("09:20", "09:55"),
    ("10:00", "10:35"),
    ("10:40", "11:15"),
    ("11:30", "12:05"),
    ("12:10", "12:45"),
    ("12:50", "13:25"),
    ("13:30", "14:05"),
    ("14:10", "14:45"),
    ("14:50", "15:25"),
]

schedule = {
    0: [(1,"Англійська"), (2,"Англійська"), (3,"Фізкультура"),
        (4,"Інтегрований курс"), (5,"Математика"), (6,"Математика")],

    1: [(1,"Музичне мистецтво"), (2,"Українська мова"),
        (3,"Українська мова"), (4,"Географія"),
        (5,"Географія"), (6,"Польська мова")],

    2: [(1,"Технології"), (2,"Технології"),
        (3,"Фізкультура"), (4,"Інформатика"),
        (5,"Українська література"),
        (6,"Українська література"),
        (7,"Англійська")],

    3: [(1,"Історія України"), (2,"Історія України"),
        (3,"Математика"), (4,"Математика"),
        (5,"Пізнаємо природу")],

    4: [(1,"Українська мова"), (2,"Українська мова"),
        (3,"Фізкультура"), (4,"Математика"),
        (5,"Вчимося жити разом")]
}

# ---------------- КЛАВІАТУРИ ----------------
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
        parts = name.split()

        if len(parts) < 2:
            await message.answer("🤭 Це не нік у TikTok.\nПотрібне прізвище та ім’я.")
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

        lessons = schedule[today]
        lessons_text = ""

        for lesson_number, lesson in lessons:
            start, end = lesson_times[lesson_number - 1]
            lessons_text += f"{lesson_number}. {lesson} ({start}-{end})\n"

        first_start = lesson_times[lessons[0][0] - 1][0]
        last_end = lesson_times[lessons[-1][0] - 1][1]

        await message.answer(
            f"📚 Сьогодні {len(lessons)} уроків\n"
            f"Початок о {first_start}\n"
            f"Закінчення о {last_end}\n\n"
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
            start, end = lesson_times[lesson_number - 1]
            start_t = datetime.strptime(start, "%H:%M").time()
            end_t = datetime.strptime(end, "%H:%M").time()

            if start_t <= now <= end_t:
                await message.answer(
                    f"Зараз {lesson_number} урок 📖\n"
                    f"{lesson}\n"
                    f"{start}-{end}"
                )
                return

        await message.answer("Перерва 😎")
        return

    # ---- РЕЙТИНГ ----
    if text == "🏆 Рейтинг активності":

        if not usage_stats:
            await message.answer("Поки що всі сонні 😴")
            return

        ranking = []

        for uid, stats in usage_stats.items():
            total = stats["schedule"] + stats["current"]
            name = user_names.get(uid, "Невідомий")
            ranking.append((name, total))

        ranking.sort(key=lambda x: x[1], reverse=True)

        text_result = "🏆 Рейтинг активності:\n\n"

        for i, (name, total) in enumerate(ranking[:5], start=1):
            text_result += f"{i}. {name} — {total}\n"

        text_result += "\nДиректор усе бачить 👀"

        await message.answer(text_result)
        return


# ---------------- ЗАПУСК ----------------
async def main():
    load_students()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
