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

creds = Credentials.from_service_account_file(
    "service_account.json",
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
    0: ["Англійська","Англійська","Фізкультура","Інтегрований курс","Математика","Математика"],
    1: ["Музичне мистецтво","Українська мова","Українська мова","Географія","Географія","Польська мова"],
    2: ["Технології","Технології","Фізкультура","Інформатика","Українська література","Українська література","Англійська"],
    3: ["Історія України","Історія України","Математика","Математика","Пізнаємо природу"],
    4: ["Українська мова","Українська мова","Фізкультура","Математика","Вчимося жити разом"]
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

    for i, (start, end) in enumerate(lesson_times):
        start_t = datetime.strptime(start, "%H:%M").time()
        end_t = datetime.strptime(end, "%H:%M").time()

        if start_t <= now <= end_t:
            if i < len(schedule[today]):
                return i, schedule[today][i]

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
        user_names[user_id] = text
        save_student(user_id, text)
        user_states[user_id] = "menu"
        await message.answer(f"Збережено як: {text} ✅", reply_markup=main_kb)
        return

    if text == "📅 Розклад":
        today = datetime.now().weekday()
        if today in schedule:
            lessons = ""
            for i, lesson in enumerate(schedule[today]):
                start, end = lesson_times[i]
                lessons += f"{i+1}. {lesson} ({start}-{end})\n"
            await message.answer(f"📚 Сьогодні:\n\n{lessons}")
        else:
            await message.answer("Сьогодні уроків немає 😎")
        return

    if text == "⏰ Який урок зараз?":
        num, lesson = get_current_lesson()
        if lesson:
            await message.answer(f"Зараз {lesson} 📖")
        else:
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

async def main():
    load_students()
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())