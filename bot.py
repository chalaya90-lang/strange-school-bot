import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

TOKEN = "8582009214:AAEwkSe7XPSvnt42rWQoJktYRmhQU3iwtfE"
ADMIN_IDS = {123456789, 5687913918}  # ID вчителя і старости

# ---------------- GOOGLE SHEETS ----------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

import os
import json
from google.oauth2.service_account import Credentials
creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(
    creds_info,
    scopes=SCOPES
)
gc = gspread.authorize(creds)
sheet = gc.open("Відсутність учнів").sheet1
# ------------------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_states = {}
user_names = {}
users = set()
usage_stats = {}
def update_usage(user_id, action):
    if user_id not in usage_stats:
        usage_stats[user_id] = {
            "schedule": 0,
            "current": 0
        }

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
    0: [(1,"Англійська"),
        (2,"Англійська"),
        (3,"Фізкультура"),
        (4,"Інтегрований курс"),
        (5,"Математика"),
        (6,"Математика")],

    1: [(1,"Музичне мистецтво"),
        (2,"Українська мова"),
        (3,"Українська мова"),
        (4,"Географія"),
        (5,"Географія"),
        (6,"Польська мова")],

    2: [(1,"Технології"),
        (2,"Технології"),
        (3,"Фізкультура"),
        (4,"Інформатика"),
        (5,"Українська література"),
        (6,"Українська література"),
        (7,"Англійська")],

    3: [(1,"Історія України"),
        (2,"Історія України"),
        (3,"Математика"),
        (4,"Математика"),
        (5,"Пізнаємо природу")],

    4: [(1,"Українська мова"),
        (2,"Українська мова"),
        (3,"Фізкультура"),
        (4,"Математика"),
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
        [KeyboardButton(text="📊 Статистика")]
        [KeyboardButton(text="🏆 Рейтинг активності")],
    ],
    resize_keyboard=True
)

back_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅ Назад")]],
    resize_keyboard=True
)

# ---------------- ДОПОМІЖНІ ----------------
def load_students():
    try:
        with open("students.txt", "r", encoding="utf-8") as f:
            for line in f:
                user_id, name = line.strip().split("|")
                user_names[int(user_id)] = name
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

def get_current_lesson():
    now = datetime.now().time()
    today = datetime.now().weekday()

    if today not in schedule:
        return None, None

    for lesson_number, lesson in schedule[today]:

        if lesson_number - 1 < len(lesson_times):
            start, end = lesson_times[lesson_number - 1]

            start_t = datetime.strptime(start, "%H:%M").time()
            end_t = datetime.strptime(end, "%H:%M").time()

            if start_t <= now <= end_t:
                return lesson_number, lesson

    return None, None

# ---------------- НАГАДУВАННЯ ----------------
async def reminder_loop():
    while True:
        now = datetime.now()

        for i, (start, _) in enumerate(lesson_times):
            lesson_time = datetime.strptime(start, "%H:%M")
            notify_time = lesson_time - timedelta(minutes=5)

            if now.hour == notify_time.hour and now.minute == notify_time.minute:
                today = now.weekday()
                if today in schedule and i < len(schedule[today]):
                    lesson = schedule[today][i]
                    for user_id in users:
                        await bot.send_message(
                            user_id,
                            f"⏳ Через 5 хв починається {i+1} урок — {lesson}"
                        )

        await asyncio.sleep(30)

# ---------------- HANDLER ----------------
@dp.message()
async def handler(message: types.Message):
    text = message.text
    user_id = message.chat.id
    users.add(user_id)

    if text == "/start":
        if user_id not in user_names:
            user_states[user_id] = "waiting_name"
            await message.answer("Введіть своє прізвище та ім’я ✍️")
            return

        user_states[user_id] = "menu"
        await message.answer("Головне меню 📚", reply_markup=main_kb)
        return

    if text == "⬅ Назад":
        user_states[user_id] = "menu"
        await message.answer("Головне меню 📚", reply_markup=main_kb)
        return

    state = user_states.get(user_id)

    if state == "waiting_name":
    
        name = text.strip()
    
        # Перевірка: мінімум 2 слова
        parts = name.split()
    
        if len(parts) < 2:
            await message.answer(
                "🤭 Ні-ні-ні.\n"
                "Це не нік у TikTok.\n"
                "Потрібне справжнє прізвище та ім’я."
            )
            return

    # Перевірка: тільки літери
    if not all(part.replace("'", "").isalpha() for part in parts):
        await message.answer(
            "😑 Це що, пароль від Wi-Fi?\n"
            "Введи нормальне прізвище та ім’я без цифр і символів."
        )
        return

    # Якщо все ок
    user_names[user_id] = name
    save_student(user_id, name)
    user_states[user_id] = "menu"

    await message.answer(
        f"Збережено як: {name} ✅\n"
        "Тепер система знає, хто ти 😉",
        reply_markup=main_kb
    )
    return

if text == "📅 Розклад":

    update_usage(user_id, "schedule")

    today = datetime.now().weekday()

    if today in schedule:
        lessons = schedule[today]

        if not lessons:
            await message.answer("Сьогодні уроків немає 😎")
            return

        lessons_text = ""

        for lesson_number, lesson in lessons:
            if lesson_number - 1 < len(lesson_times):
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
    else:
        await message.answer("Сьогодні уроків немає 😎")

    return

        lessons_text = ""

        for lesson_number, lesson in lessons:
            if lesson_number - 1 < len(lesson_times):
                start, end = lesson_times[lesson_number - 1]
                lessons_text += f"{lesson_number}. {lesson} ({start}-{end})\n"

        # Перший і останній урок
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
    else:
        await message.answer("Сьогодні уроків немає 😎")

    return

    if text == "⏰ Який урок зараз?":
        num, lesson, start, end = get_current_lesson()
    
        update_usage(user_id, "current")  # ← ОТУТ
    
        if lesson:
            await message.answer(
                f"Зараз {num} урок 📖\n"
                f"{lesson}\n"
                f"{start}-{end}"
            )
        else:
            await message.answer("Зараз перерва або уроків немає 😌")
    
        return

    for lesson_number, lesson in schedule[today]:

        if lesson_number - 1 < len(lesson_times):
            start, end = lesson_times[lesson_number - 1]

            start_t = datetime.strptime(start, "%H:%M").time()
            end_t = datetime.strptime(end, "%H:%M").time()

            if start_t <= now <= end_t:
                await message.answer(
                    f"Зараз {lesson_number} урок 📖\n{lesson}\n{start}-{end}"
                )
                return

    await message.answer("Зараз перерва або уроків немає 😌")
    return

    if text == "🔔 Дзвінки":
        times = "\n".join([f"{i+1}. {s}-{e}" for i, (s, e) in enumerate(lesson_times)])
        await message.answer(f"🔔 Скорочені дзвінки:\n\n{times}")
        return

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
            text_result += f"{i}. {name} — {total} звернень\n"

        text_result += "\nДиректор усе бачить 👀"

        await message.answer(text_result)
        return

    ranking = []

    for uid, stats in usage_stats.items():
        total = stats["schedule"] + stats["current"]
        name = user_names.get(uid, "Невідомий")
        ranking.append((name, total))

    ranking.sort(key=lambda x: x[1], reverse=True)

    text_result = "🏆 Рейтинг активності:\n\n"

    for i, (name, total) in enumerate(ranking[:5], start=1):
        text_result += f"{i}. {name} — {total} звернень\n"

    text_result += "\nДиректор все бачить 👀"

    await message.answer(text_result)
    return

    ranking = []

    for uid, stats in usage_stats.items():
        total = stats["schedule"] + stats["current"]
        name = user_names.get(uid, "Невідомий")
        ranking.append((name, total))

    ranking.sort(key=lambda x: x[1], reverse=True)

    text_result = "🏆 Рейтинг активності:\n\n"

    for i, (name, total) in enumerate(ranking[:5], start=1):
        text_result += f"{i}. {name} — {total} звернень\n"

    text_result += "\nДиректор все бачить 👀"

    await message.answer(text_result)
    return


# 🔔 ОСЬ ТУТ ВСТАВЛЯЄМО НАГАДУВАННЯ
async def daily_schedule_reminder():
    while True:
        now = datetime.now()

        # тільки будні
        if now.weekday() < 5 and now.hour == 7 and now.minute == 50:

            lessons_today = schedule.get(now.weekday(), [])

            if lessons_today:
                first_lesson = lessons_today[0]
                message_text = (
                    f"📚 Сьогодні {len(lessons_today)} уроків\n"
                    f"Перший: {first_lesson}"
                )

                for user_id in users:
                    try:
                        await bot.send_message(user_id, message_text)
                    except:
                        pass

            await asyncio.sleep(60)

        await asyncio.sleep(20)


async def main():
    load_students()
    asyncio.create_task(daily_schedule_reminder())  # ← ОСЬ ТУТ
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())






















