import asyncio
import os
import json
import re

from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

import gspread
from google.oauth2.service_account import Credentials


# ---------- ЧАСОВИЙ ПОЯС ----------

kyiv = pytz.timezone("Europe/Kyiv")


# ---------- НАЛАШТУВАННЯ ----------

TOKEN = "8582009214:AAEwkSe7XPSvnt42rWQoJktYRmhQU3iwtfE"

ADMIN_NAMES = {"Марія Чала", "Лілія Шрам"}


# ---------- ДЗВІНКИ ----------

lesson_times = [
("08:00","08:35"),
("08:40","09:15"),
("09:20","09:55"),
("10:00","10:35"),
("10:40","11:15"),
("11:30","12:05"),
("12:10","12:45"),
("12:50","13:25"),
("13:30","14:05"),
("14:10","14:45"),
("14:50","15:25")
]


# ---------- GOOGLE SHEETS ----------

SCOPES = [
"https://www.googleapis.com/auth/spreadsheets",
"https://www.googleapis.com/auth/drive"
]

creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)

gc = gspread.authorize(creds)

sheet = gc.open("Відсутність учнів").sheet1
schedule_sheet = gc.open("Відсутність учнів").worksheet("Розклад")


# ---------- BOT ----------

bot = Bot(token=TOKEN)
dp = Dispatcher()

users=set()
user_names={}
user_states={}
usage_stats={}

schedule_cache=[]


# ---------- КЛАВІАТУРА ----------

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


# ---------- СТАТИСТИКА ----------

def update_usage(user_id,action):

    if user_id not in usage_stats:
        usage_stats[user_id]={"schedule":0,"current":0}

    usage_stats[user_id][action]+=1


# ---------- ФАЙЛИ ----------

def load_students():

    try:
        with open("students.txt","r",encoding="utf-8") as f:

            for line in f:
                uid,name=line.strip().split("|")
                user_names[int(uid)]=name

    except:
        pass


def save_student(user_id,name):

    with open("students.txt","a",encoding="utf-8") as f:
        f.write(f"{user_id}|{name}\n")


def save_absence(name,reason):

    now=datetime.now(kyiv).strftime("%d.%m.%Y %H:%M")

    with open("absences.txt","a",encoding="utf-8") as f:
        f.write(f"{now} | {name} | {reason}\n")

    sheet.append_row([now,name,reason])


# ---------- КЕШ РОЗКЛАДУ ----------

def load_schedule():

    global schedule_cache

    rows=schedule_sheet.get_all_records()

    schedule_cache=rows


async def schedule_updater():

    while True:

        load_schedule()

        await asyncio.sleep(600)


# ---------- РОЗКЛАД СЬОГОДНІ ----------

def get_today_schedule():

    today=datetime.now(kyiv).weekday()

    lessons=[]

    for row in schedule_cache:

        try:
            day=int(row["День"])
        except:
            continue

        if day==today:
            lessons.append(row)

    lessons.sort(key=lambda x:x["Початок"])

    return lessons


# ---------- УРОК ЗАРАЗ ----------

def get_current_lesson():

    lessons=get_today_schedule()

    now=datetime.now(kyiv).time()

    for row in lessons:

        start=row["Початок"]
        end=row["Кінець"]
        subject=row["Предмет"]

        start_t=datetime.strptime(start,"%H:%M").time()
        end_t=datetime.strptime(end,"%H:%M").time()

        if start_t<=now<=end_t:
            return start,end,subject

    return None


# ---------- БУДИЛЬНИК ----------

async def morning_alarm():

    sent_today=False

    while True:

        now=datetime.now(kyiv)

        if now.hour==7 and now.minute==45 and not sent_today:

            lessons=get_today_schedule()

            if lessons:

                day_name=now.strftime("%A")

                text=f"☀️ Доброго ранку\nСьогодні {day_name}\n\n📚 Розклад:\n\n"

                for row in lessons:

                    start=row["Початок"]
                    end=row["Кінець"]
                    subject=row["Предмет"]

                    text+=f"{subject} ({start}-{end})\n"

                for user in users:

                    try:
                        await bot.send_audio(
                        user,
                        audio=FSInputFile("alarm.mp3"),
                        caption=text
                        )
                    except:
                        pass

            sent_today=True

        if now.hour==8:
            sent_today=False

        await asyncio.sleep(30)


# ---------- HANDLER ----------

@dp.message()
async def handler(message:types.Message):

    text=message.text
    user_id=message.chat.id

    users.add(user_id)

    state=user_states.get(user_id)


# ---------- БЛОКУВАННЯ БОТА БЕЗ ІМЕНІ ----------

    if user_id not in user_names and text!="/start":

        user_states[user_id]="waiting_name"

        await message.answer(
        "🚫 Стоп.\n"
        "Це не TikTok і не анонімний чат 😄\n\n"
        "Введіть своє прізвище та ім’я."
        )

        return


# ---------- START ----------

    if text=="/start":

        if user_id not in user_names:

            user_states[user_id]="waiting_name"

            await message.answer(
            "Привіт 👋\n"
            "Перед тим як користуватись ботом,\n"
            "введіть своє прізвище та ім’я ✍️"
            )

            return

        await message.answer("Головне меню 📚",reply_markup=main_kb)

        return


# ---------- РЕЄСТРАЦІЯ ----------

    if state=="waiting_name":

        name=text.strip()

        parts=name.split()

        if len(parts)<2:

            await message.answer(
            "🤨 Це не нік у TikTok.\n"
            "Напишіть **прізвище та ім’я**."
            )

            return

        if not all(re.match("^[А-Яа-яA-Za-zІіЇїЄє'-]+$",p) for p in parts):

            await message.answer(
            "😑 Тут мають бути **тільки літери**.\n"
            "Без цифр і символів."
            )

            return

        user_names[user_id]=name

        save_student(user_id,name)

        await message.answer(
        f"Записано: {name} ✅\n"
        "Тепер можна користуватись ботом.",
        reply_markup=main_kb
        )

        return


# ---------- РОЗКЛАД ----------

    if text=="📅 Розклад":

        lessons=get_today_schedule()

        if not lessons:
            await message.answer("Сьогодні уроків немає 😎")
            return

        result="📚 Сьогодні:\n\n"

        for row in lessons:

            start=row["Початок"]
            end=row["Кінець"]
            subject=row["Предмет"]

            lesson_number=None

            for i,(s,e) in enumerate(lesson_times,start=1):

                if s==start:
                    lesson_number=i
                    break

            result+=f"{lesson_number}. {subject} ({start}-{end})\n"

        await message.answer(result)

        return


# ---------- ЯКИЙ УРОК ----------

    if text=="⏰ Який урок зараз":

        lesson=get_current_lesson()

        if lesson:

            start,end,subject=lesson

            await message.answer(
            f"📖 Зараз урок\n{subject}\n{start}-{end}"
            )

        else:

            await message.answer("⏳ Зараз перерва")

        return


# ---------- ДЗВІНКИ ----------

    if text=="🔔 Дзвінки":

        result="🔔 Розклад дзвінків:\n\n"

        for i,(start,end) in enumerate(lesson_times,start=1):
            result+=f"{i}. {start}-{end}\n"

        await message.answer(result)

        return


# ---------- ВІДСУТНІСТЬ ----------

    if text=="📩 Повідомити про відсутність":

        user_states[user_id]="waiting_absence"

        await message.answer("Напишіть причину ✍️",reply_markup=back_kb)

        return


    if state=="waiting_absence":

        name=user_names.get(user_id,"Невідомий")

        save_absence(name,text)

        await message.answer("Запис додано ✅",reply_markup=main_kb)

        return


# ---------- ОГОЛОШЕННЯ ----------

    if text=="📢 Оголошення":

        name=user_names.get(user_id)

        if name not in ADMIN_NAMES:
            await message.answer("Доступ тільки для адміністрації 🔒")
            return

        user_states[user_id]="waiting_announcement"

        await message.answer("Напишіть оголошення")

        return


    if state=="waiting_announcement":

        for u in users:

            try:
                await bot.send_message(u,f"📢 ОГОЛОШЕННЯ\n\n{text}")
            except:
                pass

        await message.answer("Оголошення розіслано")

        return


# ---------- MAIN ----------

async def main():

    load_students()

    load_schedule()

    asyncio.create_task(schedule_updater())
    asyncio.create_task(morning_alarm())

    await dp.start_polling(bot)


if __name__=="__main__":

    asyncio.run(main())
