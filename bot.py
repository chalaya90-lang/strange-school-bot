import asyncio
import os
import json
from datetime import datetime

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


# ---------------- СКОРОЧЕНІ ДЗВІНКИ ----------------
lesson_times = [
    ("08:00", "08:35"),  # 1
    ("08:40", "09:15"),  # 2
    ("09:20", "09:55"),  # 3
    ("10:00", "10:35"),  # 4
    ("10:40", "11:15"),  # 5
    ("11:30", "12:05"),  # 6
    ("12:10", "12:45"),  # 7
    ("12:50", "13:25"),  # 8
    ("13:30", "14:05"),  # 9
    ("14:10", "14:45"),  # 10
    ("14:50", "15:25"),  # 11
]

# ---------------- РОЗКЛАД ----------------
schedule = {
    0: [  # понеділок
        (6,"Англійська мова"),
        (7,"Англійська мова"),
        (8,"Фізична культура"),
        (9,"Інтегрований курс"),
        (10,"Математика"),
        (11,"Математика"),
    ],

    1: [  # вівторок
        (1,"Музичне мистецтво"),
        (6,"Українська мова"),
        (7,"Українська мова"),
        (8,"Географія"),
        (9,"Географія"),
        (10,"Польська мова"),
    ],

    2: [  # середа
        (1,"Технології"),
        (2,"Технології"),
        (3,"Фізична культура"),
        (5,"Інформатика"),
        (6,"Українська література"),
        (7,"Українська література"),
        (8,"Англійська мова"),
    ],

    3: [  # четвер
        (6,"Історія України"),
        (7,"Історія України"),
        (8,"Математика"),
        (9,"Математика"),
        (10,"Пізнаємо природу"),
    ],

    4: [  # пʼятниця
        (6,"Українська мова"),
        (7,"Українська мова"),
        (8,"Фізична культура"),
        (9,"Математика"),
        (10,"Вчимося жити разом"),
    ]
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
            await message.answer("🤭 Це не нік. Потрібне прізвище та ім’я.")
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

    today = datetime.now().weekday()

    if today not in schedule:
        await message.answer("Сьогодні уроків немає 😎")
        return

    lessons = sorted(schedule[today], key=lambda x: x[0])

    lessons_text = ""

    for lesson_number, lesson in lessons:

        if lesson_number <= len(lesson_times):

            start, end = lesson_times[lesson_number - 1]

            lessons_text += f"{lesson_number}. {lesson} ({start}-{end})\n"

    first_num, _ = lessons[0]
    last_num, _ = lessons[-1]

    first_start = lesson_times[first_num - 1][0]
    last_end = lesson_times[last_num - 1][1]

    await message.answer(
        f"📚 Сьогодні {len(lessons)} уроків\n"
        f"Початок о {first_start}\n"
        f"Закінчення о {last_end}\n\n"
        f"{lessons_text}"
    )

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

    # ---- ДЗВІНКИ ----
    if text == "🔔 Дзвінки":
        times = "\n".join(
            [f"{i+1}. {start}-{end}" for i, (start, end) in enumerate(lesson_times)]
        )
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

    # ---- ОГОЛОШЕННЯ ----
    if text == "📢 Оголошення":
        if user_id not in ADMIN_IDS:
            await message.answer("Доступ тільки для адміністрації 🔒")
            return
        user_states[user_id] = "waiting_announcement"
        await message.answer("Введіть текст оголошення 📝", reply_markup=back_kb)
        return

    if state == "waiting_announcement":
        for u in users:
            await bot.send_message(u, f"📢 ОГОЛОШЕННЯ:\n\n{text}")
        user_states[user_id] = "menu"
        await message.answer("Оголошення розіслано ✅", reply_markup=main_kb)
        return

    # ---- СТАТИСТИКА ----
    if text == "📊 Статистика":
        if user_id not in ADMIN_IDS:
            await message.answer("Доступ тільки для адміністрації 🔒")
            return

        today = datetime.now().strftime("%d.%m.%Y")
        count = 0

        try:
            with open("absences.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if today in line:
                        count += 1
        except FileNotFoundError:
            await message.answer("Записів ще немає")
            return

        await message.answer(f"📊 Відсутніх сьогодні: {count}")
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

        result = "🏆 Рейтинг активності:\n\n"

        for i, (name, total) in enumerate(ranking[:5], start=1):
            result += f"{i}. {name} — {total}\n"

        result += "\nДиректор усе бачить 👀"

        await message.answer(result)
        return


# ---------------- ЗАПУСК ----------------
async def main():
    load_students()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())



