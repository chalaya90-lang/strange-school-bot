import asyncio
import os
import json
import random
from datetime import datetime, timedelta
import pytz

from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import FSInputFile
from aiogram.filters import Command

import gspread
from google.oauth2.service_account import Credentials

# ================= НАЛАШТУВАННЯ =================

kyiv = pytz.timezone("Europe/Kyiv")
TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ТУТ")

# Адміни: реальне ім'я → нік в боті
ADMIN_DISPLAY = {
    "Марія Чала":  "👩‍🏫 Марія Чала",
    "Лілія Шрам":  "👩‍🏫 Лілія Шрам",
    "Чала Любов":  "⚡️ Од",
}
ADMIN_NAMES = set(ADMIN_DISPLAY.keys())

# Твій Telegram ID — отримаєш після /myid
NOTIFY_ADMIN_ID = int(os.getenv("NOTIFY_ADMIN_ID", "1047959580"))

# ================= ДЗВІНКИ =================

BELLS = [
    (1,  "08:00", "08:35"),
    (2,  "08:40", "09:15"),
    (3,  "09:20", "09:55"),
    (4,  "10:00", "10:35"),
    (5,  "10:40", "11:15"),
    (6,  "11:30", "12:05"),
    (7,  "12:10", "12:45"),
    (8,  "12:50", "13:25"),
    (9,  "13:30", "14:05"),
    (10, "14:10", "14:45"),
    (11, "14:50", "15:25"),
]

# час початку → номер уроку
BELLS_MAP = {start: num for num, start, _ in BELLS}

# ================= ЧЕЛЕНДЖІ =================

CHALLENGES = [
    "Скажи комусь із класу щось приємне 😊",
    "Зроби 20 присідань прямо зараз 🏋️",
    "Намалюй щось за 1 хвилину ✏️",
    "Вивчи одне нове слово англійською 🇬🇧",
    "Напиши 3 речі, за які ти вдячний сьогодні 🙏",
    "Зроби 10 стрибків на місці 🤸",
    "Прочитай 2 сторінки будь-якої книги 📚",
    "Посміхнись першому, кого зустрінеш 😄",
    "Вимкни телефон на 15 хвилин і просто відпочинь 🧘",
    "Зроби щось корисне для свого класу 🏫",
    "Запитай когось як справи і справді вислухай 👂",
    "Придумай і розкажи класу кумедний жарт 😂",
    "Допоможи однокласнику з чимось без прохання 🤝",
    "Напиши листа собі в майбутнє ✉️",
    "Зроби щось вперше в житті — навіть маленьке 🌟",
]

DAYS_UA = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]

# ================= ЦІКАВІ ФАКТИ =================
# Зберігаємо індекс поточного факту в Банк (ключ: fact_index)
# Коли залишається 10 фактів — сповіщаємо адміна

FACTS = [
    "🐙 Восьминоги мають три серця і блакитну кров!",
    "🍯 Мед ніколи не псується — у єгипетських пірамідах знайшли їстівний мед віком 3000 років!",
    "🦷 Слони — єдині тварини, які не вміють стрибати. Навіть з розгону!",
    "🌊 Океани покривають 71% поверхні Землі, але людство дослідило лише 5% їх глибин.",
    "⚡️ Блискавка нагріває повітря до 30 000°C — це в 5 разів гарячіше, ніж поверхня Сонця!",
    "🐌 Равлик може спати до 3 років поспіль під час посухи.",
    "🌙 На Місяці немає вітру, тому сліди астронавтів Apollo збережуться ще мільйони років.",
    "🦈 У акул немає кісток — їх скелет повністю складається з хрящів.",
    "🍓 Полуниця технічно не є ягодою, а банан — є!",
    "🐘 Слони вміють розпізнавати себе у дзеркалі — це вміють лише найрозумніші тварини.",
    "💧 Гаряча вода замерзає швидше за холодну. Це називається ефект Мпемби!",
    "🦋 Метелики відчувають смак їжі ногами.",
    "🌍 Якби всі мурахи на Землі зважили, їхня маса дорівнювала б масі всіх людей.",
    "🐬 Дельфіни сплять із одним відкритим оком — половина мозку чергує відпочинок.",
    "🎵 Коров'яче молоко дають краще, якщо корови слухають повільну музику.",
    "🧠 Мозок людини генерує близько 70 000 думок на день.",
    "🌵 Кактус може зберігати до 3000 літрів води у своєму стеблі.",
    "🦁 Лев може спати до 20 годин на добу. Мрія! 😴",
    "🐧 Пінгвіни роблять пропозицію своїм партнерам за допомогою камінців.",
    "🌈 Веселку неможливо побачити опівдні — вона завжди перед тобою протилежно до Сонця.",
    "🍕 Піца була винайдена в Неаполі, Італія, у 1889 році.",
    "🐝 Бджола повинна відвідати 2 мільйони квіток, щоб виробити 500 г меду.",
    "🦊 Лисиці використовують магнітне поле Землі для точного стрибка на здобич.",
    "🌺 Бамбук росте зі швидкістю до 91 см на добу — найшвидша рослина на планеті!",
    "🐙 Восьминоги можуть відкривати скляні банки зсередини.",
    "🎭 Сміх заразний — мозок автоматично готується сміятись почувши чужий сміх.",
    "🌟 Сонце настільки велике, що в ньому помістилось би 1,3 мільйона Земель.",
    "🐠 Риба-клоун може змінити стать з чоловічої на жіночу при потребі.",
    "🍦 Морозиво існує вже понад 2000 років — перші рецепти були в Китаї!",
    "🦜 Папуги живуть до 80 років і можуть вивчити понад 1000 слів.",
    "⚽ М'яч для футболу складається рівно з 32 панелей — 20 шестикутників і 12 п'ятикутників.",
    "🌊 Найглибше місце океану — Маріанська западина — глибше, ніж Евереста заввишки!",
    "🐻 Ведмеді не впадають у справжню сплячку — їх температура тіла знижується лише трохи.",
    "🦩 Фламінго рожеві через їжу — вони їдять рожевих рачків та водорості.",
    "🍌 Банани злегка радіоактивні через вміст калію-40. Але це абсолютно безпечно!",
    "🐦 Колібрі — єдиний птах, який може летіти назад.",
    "🌍 На Землі більше дерев, ніж зірок у Чумацькому Шляху.",
    "🦷 Зуби акули відновлюються протягом усього життя — за своє життя акула змінює до 50 000 зубів!",
    "🎮 Перша відеогра була створена в 1958 році — це був тенісний симулятор.",
    "🌙 Якби Місяць зник, Земля почала б обертатись значно швидше — доба тривала б 8 годин.",
    "🐳 Серце синього кита розміром з невеликий автомобіль і б'ється лише 8-10 разів на хвилину.",
    "🍫 Шоколад був спочатку напоєм — ацтеки пили гіркий какао з перцем!",
    "🌿 Трава «чує» коли її косять і виділяє хімічні сигнали — це той свіжий запах!",
    "🐁 Щури сміються під час ігор — але на частотах, які людське вухо не чує.",
    "🚀 У космосі немає звуку — там абсолютна тиша, бо нема повітря для звукових хвиль.",
    "🦋 Гусінь повністю розчиняється всередині кокона і збирається наново як метелик.",
    "🌍 Антарктида — найбільша пустеля на Землі, хоч там і є лід.",
    "🐊 Крокодили ковтають каміння, щоб краще занурюватись у воду — як баласт.",
    "🍎 Яблука на 25% складаються з повітря — саме тому вони плавають у воді.",
    "🦑 Кальмар-вогнетіл світиться у темряві завдяки спеціальним клітинам.",
    "🌡️ Рекордна температура на Землі — +56,7°C у Долині Смерті, США (1913 рік).",
    "🎨 Перший олівець був виготовлений у 1565 році в Англії.",
    "🐬 Дельфіни мають імена — вони звертаються один до одного унікальними свистами.",
    "🌊 Вода може текти вгору — у тонких трубках завдяки капілярному ефекту.",
    "🦅 Орел бачить у 8 разів чіткіше за людину і може помітити кролика з 3 км.",
    "🍉 Кавун — це не фрукт і не овоч, а ягода. Як і помідор!",
    "🐝 Бджоли танцюють, щоб показати де знаходяться квіти — це справжня мова!",
    "🌙 На Місяці немає атмосфери, тому там одночасно може бути -170°C в тіні і +130°C на сонці.",
    "🦎 Хамелеон змінює колір не для маскування, а для спілкування і регуляції температури.",
    "🎸 Гітара була винайдена в Іспанії приблизно в XV столітті.",
    "🌺 Квіти лотоса можуть підтримувати температуру своїх пелюсток навіть у холодну погоду.",
    "🐟 Золота рибка має пам'ять не 3 секунди, а до 5 місяців!",
    "🚂 Перший поїзд розвивав швидкість лише 8 км/год — повільніше за велосипед.",
    "🦠 В одній краплі морської води міститься мільйон бактерій.",
    "🌍 Якщо розтягнути всі нейрони мозку людини в лінію, вийде близько 900 км.",
    "🍋 Лимони містять більше цукру ніж полуниця — але кислота маскує смак.",
    "🐺 Вовки можуть чути звуки на відстані до 10 км.",
    "🌊 Кожну секунду блискавка вдаряє в Землю близько 100 разів.",
    "🦁 Левиця виконує 90% полювання у прайді, хоча лев отримує їжу першим.",
    "🎯 Людське тіло випромінює достатньо тепла за 30 хвилин, щоб закип'ятити пів літра води.",
    "🌵 Деякі кактуси в пустелі цвітуть лише раз на 100 років.",
    "🐠 Морські коники — єдині тварини, де самець виношує потомство.",
    "🍀 Шанс знайти чотирилисний конюшник — 1 до 10 000.",
    "🦒 Жирафа має таку ж кількість шийних хребців як і людина — 7.",
    "🌟 Вся ДНК людини розтягнута була б завдовжки 2 метри, а в кожній клітині вона скручена.",
    "🐋 Горбаті кити складають нові пісні щороку і навчають одне одного.",
    "🍇 Виноград вибухає в мікрохвильовій печі — науковці спеціально вивчали чому!",
    "🌍 Африканський слон вагою 6 тонн може стояти на трьох ногах для відпочинку.",
    "🦋 Деякі метелики мігрують на відстань до 4800 км — як монарх з Канади до Мексики.",
    "🎻 Скрипка Страдіварі XVII століття досі звучить краще за сучасні — вчені не знають чому.",
    "🌊 Найбільша хвиля, зафіксована людьми, була висотою 524 метри — на Алясці у 1958 році.",
    "🐘 Слони вміють плакати і проявляти горе — вони навіть повертаються до кісток загиблих.",
]


# ================= МАГАЗИН =================

SHOP_ITEMS = [
    {"id": "compliment", "emoji": "🃏", "name": "Анонімний компліментик",  "desc": "Бот надішле анонімний комплімент однокласнику", "price": 10},
    {"id": "seat",       "emoji": "🪑", "name": "Вибір місця в класі",     "desc": "Сядеш де хочеш один день",                     "price": 50},
    {"id": "host",       "emoji": "🎤", "name": "Ведучий уроку",           "desc": "Станеш ведучим на одному уроці",                "price": 80},
    {"id": "homework",   "emoji": "😴", "name": "Пропустити домашнє",      "desc": "Один раз можна не робити домашнє",              "price": 100},
    {"id": "cinema",     "emoji": "🎬", "name": "Кінодень",                "desc": "Клас голосує за фільм і дивиться разом",        "price": 200},
    {"id": "pizza",      "emoji": "🍕", "name": "Ігродень з піцою",        "desc": "Весь клас грає і їсть піцу!",                  "price": 500},
    {"id": "gift",       "emoji": "🎁", "name": "Подарувати монети",       "desc": "Передати свої монети іншому учню",              "price": 0},
]

# ================= РІВНІ =================

LEVELS = [
    (0,   "🌱 Новачок"),
    (50,  "⭐️ Активіст"),
    (150, "🔥 Ентузіаст"),
    (300, "💎 Легенда класу"),
    (500, "👑 Суперзірка"),
]

def get_level(coins: int) -> str:
    level = LEVELS[0][1]
    for threshold, name in LEVELS:
        if coins >= threshold:
            level = name
    return level

# ================= GOOGLE SHEETS =================
#
# Таблиця "Відсутність учнів", аркуші:
#
# "Користувачі"  → user_id | username | name | coins | registered_at
# "Банк"         → key | value   (рядок: bank | 0)
# "Ідеї"         → date | name | idea
# "Розклад"      → День | Початок | Кінець | Предмет
# "Відсутність"  → (існуючий)
# "Покупки"      → date | name | item | price
# "Скарги"       → date | text
# "Свято"        → Прізвище | Ім'я | Дата (ДД.ММ)
# "Кошики"       → item_id | item_name | price | collected | contributors (JSON)

gc = None
users_sheet      = None
bank_sheet       = None
ideas_sheet      = None
schedule_sheet   = None
absence_sheet    = None
purchases_sheet  = None
complaints_sheet = None
holidays_sheet   = None
baskets_sheet    = None

def init_google():
    global gc, users_sheet, bank_sheet, ideas_sheet, schedule_sheet
    global absence_sheet, purchases_sheet, complaints_sheet, holidays_sheet, baskets_sheet
    try:
        creds = Credentials.from_service_account_info(
            json.loads(os.getenv("GOOGLE_CREDENTIALS=")),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
        )
        gc = gspread.authorize(creds)
        book             = gc.open("Відсутність учнів")
        users_sheet      = book.worksheet("Користувачі")
        bank_sheet       = book.worksheet("Банк")
        ideas_sheet      = book.worksheet("Ідеї")
        schedule_sheet   = book.worksheet("Розклад")
        absence_sheet    = book.worksheet("Відсутність")
        purchases_sheet  = book.worksheet("Покупки")
        complaints_sheet = book.worksheet("Скарги")
        holidays_sheet   = book.worksheet("Свято")
        baskets_sheet    = book.worksheet("Кошики")
        print("GOOGLE OK ✅")
    except Exception as e:
        print("GOOGLE ERROR ❌", e)

# ================= КОРИСТУВАЧІ =================

def get_all_users() -> dict:
    if not users_sheet:
        return {}
    rows = users_sheet.get_all_records()
    return {
        str(r["user_id"]): {
            "username": str(r.get("username", "")),
            "name":     str(r.get("name", "")),
            "coins":    int(r.get("coins", 0)),
        }
        for r in rows
    }

def find_user_row(user_id: str) -> int | None:
    if not users_sheet:
        return None
    for i, v in enumerate(users_sheet.col_values(1)):
        if str(v) == str(user_id):
            return i + 1
    return None

def is_registered(user_id: str) -> bool:
    return find_user_row(user_id) is not None

def register_user(user_id: str, username: str, name: str):
    if not users_sheet:
        return
    row = find_user_row(user_id)
    now = datetime.now(kyiv).strftime("%d.%m.%Y %H:%M")
    if row is None:
        users_sheet.append_row([user_id, username, name, 0, now])
    else:
        users_sheet.update(f"B{row}:C{row}", [[username, name]])

def get_coins(user_id: str) -> int:
    row = find_user_row(user_id)
    if not row or not users_sheet:
        return 0
    return int(users_sheet.cell(row, 4).value or 0)

def set_coins(user_id: str, amount: int):
    row = find_user_row(user_id)
    if row and users_sheet:
        users_sheet.update_cell(row, 4, max(0, amount))

def add_coins(user_id: str, amount: int):
    set_coins(user_id, get_coins(user_id) + amount)

def remove_coins_from(user_id: str, amount: int):
    set_coins(user_id, max(0, get_coins(user_id) - amount))

def get_user_real_name(user_id: str) -> str:
    row = find_user_row(user_id)
    if not row or not users_sheet:
        return ""
    return users_sheet.cell(row, 3).value or ""

def get_user_name(user_id: str) -> str:
    raw = get_user_real_name(user_id)
    return ADMIN_DISPLAY.get(raw, raw) or "???"

def is_admin(user_id: str) -> bool:
    return get_user_real_name(user_id) in ADMIN_NAMES

def find_user_by_username(username: str) -> str | None:
    if not users_sheet:
        return None
    clean = username.lstrip("@").lower()
    for i, u in enumerate(users_sheet.col_values(2)):
        if str(u).lower() == clean:
            return str(users_sheet.cell(i + 1, 1).value)
    return None

# ================= БАНК =================

def get_bank_value(key: str, default: str = "0") -> str:
    if not bank_sheet:
        return default
    for i, k in enumerate(bank_sheet.col_values(1)):
        if k == key:
            return bank_sheet.cell(i + 1, 2).value or default
    return default

def set_bank_value(key: str, value: str):
    if not bank_sheet:
        return
    for i, k in enumerate(bank_sheet.col_values(1)):
        if k == key:
            bank_sheet.update_cell(i + 1, 2, value)
            return
    bank_sheet.append_row([key, value])

def get_class_bank() -> int:
    return int(get_bank_value("bank", "0"))

def set_class_bank(amount: int):
    set_bank_value("bank", str(max(0, amount)))

# ================= АКТИВНІ РЕЖИМИ =================

GAME_MODES = ["мем", "челендж", "добро", "лотерея"]

def get_active_modes() -> list:
    today = datetime.now(kyiv).strftime("%Y-%m-%d")
    if get_bank_value("modes_date", "") == today:
        modes_str = get_bank_value("modes", "")
        return modes_str.split(",") if modes_str else []
    new_modes = random.sample(GAME_MODES, 2)
    set_bank_value("modes", ",".join(new_modes))
    set_bank_value("modes_date", today)
    return new_modes

def is_active(mode: str) -> bool:
    return mode in get_active_modes()

# ================= РОЗКЛАД =================

def get_schedule_for_day(day_num: int) -> list:
    """Повертає список уроків для дня. day_num: 0=пн...4=пт"""
    if not schedule_sheet:
        return []
    rows = schedule_sheet.get_all_records()
    lessons = []
    for r in rows:
        if str(r.get("День", "")).strip() == str(day_num):
            start = str(r.get("Початок", "")).strip()
            end   = str(r.get("Кінець",  "")).strip()
            subj  = str(r.get("Предмет", "")).strip()
            # визначаємо номер уроку за часом початку
            num = BELLS_MAP.get(start, "?")
            if subj:
                lessons.append((num, start, end, subj))
    # сортуємо за часом початку
    lessons.sort(key=lambda x: x[1])
    return lessons

def format_schedule(lessons: list, day_name: str) -> str:
    if not lessons:
        return f"📅 {day_name}\n\nСьогодні уроків немає 🎉"
    txt = f"📅 {day_name}\n\n"
    for num, start, end, subj in lessons:
        txt += f"{num}. {subj} ({start}–{end})\n"
    return txt

# ================= КОШИКИ СПІЛЬНОЇ КУПІВЛІ =================

def get_baskets() -> list:
    """Повертає список активних кошиків."""
    if not baskets_sheet:
        return []
    rows = baskets_sheet.get_all_records()
    result = []
    for i, r in enumerate(rows):
        contributors = json.loads(r.get("contributors", "{}") or "{}")
        result.append({
            "row":          i + 2,  # +2 бо заголовок
            "item_id":      r.get("item_id", ""),
            "item_name":    r.get("item_name", ""),
            "price":        int(r.get("price", 0)),
            "collected":    int(r.get("collected", 0)),
            "contributors": contributors,
        })
    return result

def find_basket(item_id: str) -> dict | None:
    for b in get_baskets():
        if b["item_id"] == item_id:
            return b
    return None

def create_basket(item: dict):
    if not baskets_sheet:
        return
    baskets_sheet.append_row([item["id"], item["name"], item["price"], 0, "{}"])

def update_basket(row: int, collected: int, contributors: dict):
    if not baskets_sheet:
        return
    baskets_sheet.update(f"D{row}:E{row}", [[collected, json.dumps(contributors, ensure_ascii=False)]])

def delete_basket_row(row: int):
    if not baskets_sheet:
        return
    baskets_sheet.delete_rows(row)

# ================= КЛАВІАТУРИ =================

def build_main_kb(user_id: str) -> ReplyKeyboardMarkup:
    modes = get_active_modes()
    rows = [
        [KeyboardButton(text="📅 Розклад"),      KeyboardButton(text="🔔 Дзвінки")],
        [KeyboardButton(text="📩 Повідомити про відсутність")],
        [KeyboardButton(text="💡 Ідеї для класу")],
    ]
    row1 = []
    if "мем"     in modes: row1.append(KeyboardButton(text="😂 Мем дня"))
    if "челендж" in modes: row1.append(KeyboardButton(text="🎯 Челендж дня"))
    if row1: rows.append(row1)

    row2 = []
    if "добро"   in modes: row2.append(KeyboardButton(text="💌 Написати добро"))
    if "лотерея" in modes: row2.append(KeyboardButton(text="🎰 Удача"))
    if row2: rows.append(row2)

    rows.append([KeyboardButton(text="😴 Я прокинувся")])
    rows.append([KeyboardButton(text="🎰 Удача"), KeyboardButton(text="🤫 Таємний друг")])
    rows.append([KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="🧺 Спільні кошики")])
    rows.append([KeyboardButton(text="🪙 Мої монетки"), KeyboardButton(text="🏦 Банк класу")])
    rows.append([KeyboardButton(text="🏆 Рейтинг"), KeyboardButton(text="📬 Скарга")])
    if is_admin(user_id):
        rows.append([KeyboardButton(text="⚖️ Дія вчителя")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

teacher_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Плюс учню"),    KeyboardButton(text="➖ Мінус учню")],
        [KeyboardButton(text="💸 Штраф класу"),  KeyboardButton(text="🕊️ Амністія")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True
)

def shop_kb() -> ReplyKeyboardMarkup:
    rows = []
    for item in SHOP_ITEMS:
        price_text = f"{item['price']} 🪙" if item["price"] > 0 else "безкоштовно"
        rows.append([KeyboardButton(text=f"{item['emoji']} {item['name']} — {price_text}")])
    rows.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# ================= БОТ =================

bot = Bot(token=TOKEN)
dp  = Dispatcher()
router = Router()

user_states: dict[str, str] = {}
wake_log:    dict[str, str] = {}
gold_coin_log: str = ""

# Удача (колишнє казіно): uid → список тижнів коли грав
luck_log: dict[str, list] = {}

# комплімент: тиждень → чи вже надсилали
compliment_log: str = ""

# таємний друг: uid → uid (на поточний двотижневий цикл)
secret_friend_pairs: dict[str, str] = {}
secret_friend_cycle: str = ""  # рік + номер парного тижня  # місяць останнього золотого нагородження

def today_str() -> str:
    return datetime.now(kyiv).strftime("%Y-%m-%d")

def now_str() -> str:
    return datetime.now(kyiv).strftime("%d.%m %H:%M")

async def notify_admin(text: str):
    if NOTIFY_ADMIN_ID:
        try:
            await bot.send_message(NOTIFY_ADMIN_ID, text)
        except Exception:
            pass

# ================= HANDLERS =================

@router.message(Command("start"))
async def cmd_start(msg: types.Message):
    uid = str(msg.chat.id)
    if is_registered(uid):
        await msg.answer(f"З поверненням, {get_user_name(uid)}! 😎", reply_markup=build_main_kb(uid))
        return
    user_states[uid] = "awaiting_name"
    await msg.answer(
        "Привіт! 👋\nЯк тебе звати?\nНапиши своє прізвище та ім'я (два слова):",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(Command("myid"))
async def cmd_myid(msg: types.Message):
    await msg.answer(f"Твій ID: `{msg.chat.id}`", parse_mode="Markdown")

@router.message()
async def handler(msg: types.Message):
    uid   = str(msg.chat.id)
    text  = msg.text or ""
    uname = msg.from_user.username or ""

    # ===== РЕЄСТРАЦІЯ =====
    if user_states.get(uid) == "awaiting_name":
        name = text.strip()
        words = name.split()
        if len(words) < 2 or not all(w.isalpha() for w in words):
            await msg.answer("Введи прізвище та ім'я (тільки літери, два слова):")
            return
        register_user(uid, uname, name)
        user_states.pop(uid, None)
        display = ADMIN_DISPLAY.get(name, name)
        await msg.answer(f"Чудово, {display}! 🎉\nТепер ти в грі 🪙", reply_markup=build_main_kb(uid))
        return

    if not is_registered(uid):
        await msg.answer("Спочатку напиши /start")
        return

    # ===== СТАНИ =====

    if user_states.get(uid) == "idea":
        if ideas_sheet:
            ideas_sheet.append_row([now_str(), get_user_name(uid), text])
        add_coins(uid, 5)
        user_states.pop(uid, None)
        await msg.answer("✅ Ідею записано! +5 🪙")
        return

    if user_states.get(uid) == "meme":
        add_coins(uid, 5)
        user_states.pop(uid, None)
        await msg.answer("😂 Мем зараховано! +5 🪙")
        return

    if user_states.get(uid) == "good":
        users = get_all_users()
        others = [k for k in users if k != uid]
        if others:
            target_uid = random.choice(others)
            try:
                await bot.send_message(int(target_uid), f"💌 Хтось написав тобі:\n\n{text}")
            except Exception:
                pass
        add_coins(uid, 3)
        user_states.pop(uid, None)
        await msg.answer("+3 🪙 Повідомлення надіслано анонімно 💌")
        return

    if user_states.get(uid) == "absence":
        if absence_sheet:
            absence_sheet.append_row([now_str(), get_user_name(uid), text])
        user_states.pop(uid, None)
        await notify_admin(f"📩 Відсутність!\n{get_user_name(uid)}\nПричина: {text}")
        await msg.answer("✅ Записано! Вчитель отримав сповіщення.")
        return

    if user_states.get(uid) == "complaint":
        if complaints_sheet:
            complaints_sheet.append_row([now_str(), text])
        user_states.pop(uid, None)
        await notify_admin(f"📬 Анонімна скарга:\n\n{text}")
        await msg.answer("📬 Скаргу надіслано анонімно. Дякую 🙏")
        return

    # Подарунок крок 1
    if user_states.get(uid) == "shop_gift_who":
        target_uid = find_user_by_username(text)
        if not target_uid:
            await msg.answer("Не знайшов. Введи @username:")
            return
        if target_uid == uid:
            await msg.answer("Собі не можна 😄 Введи @username іншого:")
            return
        user_states[uid] = f"shop_gift_amount:{target_uid}"
        await msg.answer(f"Скільки монет подаруєш {get_user_name(target_uid)}?")
        return

    # Подарунок крок 2
    if user_states.get(uid, "").startswith("shop_gift_amount:"):
        target_uid = user_states[uid].split(":")[1]
        if not text.isdigit():
            await msg.answer("Введи число:")
            return
        amount = int(text)
        my_coins = get_coins(uid)
        if amount > my_coins:
            await msg.answer(f"У тебе лише {my_coins} 🪙:")
            return
        remove_coins_from(uid, amount)
        add_coins(target_uid, amount)
        user_states.pop(uid, None)
        await msg.answer(f"🎁 Ти подарував {amount} 🪙 → {get_user_name(target_uid)}!", reply_markup=build_main_kb(uid))
        try:
            await bot.send_message(int(target_uid), f"🎁 {get_user_name(uid)} подарував тобі {amount} 🪙!")
        except Exception:
            pass
        return

    # Внесок у кошик
    if user_states.get(uid, "").startswith("basket_contribute:"):
        item_id = user_states[uid].split(":")[1]
        if not text.isdigit():
            await msg.answer("Введи суму цифрами:")
            return
        amount = int(text)
        if amount <= 0:
            await msg.answer("Сума має бути більше 0:")
            return
        my_coins = get_coins(uid)
        if amount > my_coins:
            await msg.answer(f"У тебе лише {my_coins} 🪙. Введи менше:")
            return
        basket = find_basket(item_id)
        if not basket:
            user_states.pop(uid, None)
            await msg.answer("Кошик вже не існує.", reply_markup=build_main_kb(uid))
            return
        # списуємо монети
        remove_coins_from(uid, amount)
        contributors = basket["contributors"]
        contributors[uid] = contributors.get(uid, 0) + amount
        new_collected = basket["collected"] + amount
        update_basket(basket["row"], new_collected, contributors)
        user_states.pop(uid, None)

        remaining = basket["price"] - new_collected
        if remaining <= 0:
            # 🎉 Куплено!
            if purchases_sheet:
                purchases_sheet.append_row([now_str(), "Спільна купівля", basket["item_name"], basket["price"]])
            await notify_admin(
                f"🛒 Спільна купівля виконана!\n"
                f"Товар: {basket['item_name']}\n"
                f"Учасники: {', '.join(get_user_name(k) for k in contributors)}"
            )
            delete_basket_row(basket["row"])
            # повідомляємо всіх учасників
            for tuid in contributors:
                try:
                    await bot.send_message(int(tuid), f"🎉 Зібрали на {basket['item_name']}! Вчитель вже знає!")
                except Exception:
                    pass
            await msg.answer(f"🎉 Зібрали! {basket['item_name']} куплено!", reply_markup=build_main_kb(uid))
        else:
            await msg.answer(
                f"✅ Ти вніс {amount} 🪙\n"
                f"Зібрано: {new_collected}/{basket['price']} 🪙\n"
                f"Ще треба: {remaining} 🪙",
                reply_markup=build_main_kb(uid)
            )
        return

    # Вчитель плюс/мінус
    if user_states.get(uid) in ("teacher_plus", "teacher_minus"):
        parts = text.strip().split()
        if len(parts) != 2 or not parts[1].isdigit():
            await msg.answer("Формат: @username кількість\nНаприклад: @ivan 10")
            return
        uname_t, amount = parts[0], int(parts[1])
        target_uid = find_user_by_username(uname_t)
        if not target_uid:
            await msg.answer(f"Не знайшов {uname_t}.")
            return
        target_name = get_user_name(target_uid)
        if user_states[uid] == "teacher_plus":
            add_coins(target_uid, amount)
            await msg.answer(f"✅ {target_name} +{amount} 🪙", reply_markup=teacher_kb)
            try: await bot.send_message(int(target_uid), f"🎉 Вчитель нарахував тобі +{amount} 🪙!")
            except Exception: pass
        else:
            remove_coins_from(target_uid, amount)
            await msg.answer(f"✅ {target_name} -{amount} 🪙", reply_markup=teacher_kb)
            try: await bot.send_message(int(target_uid), f"⚠️ Вчитель зняв {amount} 🪙")
            except Exception: pass
        user_states.pop(uid, None)
        return

    if user_states.get(uid) == "teacher_fine":
        if not text.isdigit():
            await msg.answer("Введи суму цифрами:")
            return
        amount = int(text)
        set_class_bank(max(0, get_class_bank() - amount))
        user_states.pop(uid, None)
        await msg.answer(f"💸 З банку знято {amount} 🪙\nЗалишок: {get_class_bank()} 🪙", reply_markup=teacher_kb)
        for tuid in get_all_users():
            try: await bot.send_message(int(tuid), f"⚠️ Вчитель зняв {amount} 🪙 з банку класу!")
            except Exception: pass
        return

    # ===== ГОЛОВНЕ МЕНЮ =====

    if text == "📅 Розклад":
        now = datetime.now(kyiv)
        weekday = now.weekday()  # 0=пн
        if weekday >= 5:
            await msg.answer("Сьогодні вихідний 🎉\nУроків немає!")
            return
        lessons = get_schedule_for_day(weekday)
        day_name = DAYS_UA[weekday]
        await msg.answer(format_schedule(lessons, day_name))
        return

    if text == "🔔 Дзвінки":
        txt = "🔔 Розклад дзвінків:\n\n"
        for num, start, end in BELLS:
            txt += f"{num}. {start} – {end}\n"
        await msg.answer(txt)
        return

    if text == "📩 Повідомити про відсутність":
        user_states[uid] = "absence"
        await msg.answer("Вкажи причину відсутності:")
        return

    if text == "💡 Ідеї для класу":
        user_states[uid] = "idea"
        await msg.answer("✏️ Напиши свою ідею:")
        return

    if text == "😂 Мем дня":
        if not is_active("мем"):
            await msg.answer("Сьогодні мемів немає 🙅")
            return
        user_states[uid] = "meme"
        await msg.answer("Скинь мем (фото, гіф або текст):")
        return

    if text == "🎯 Челендж дня":
        if not is_active("челендж"):
            await msg.answer("Сьогодні без челенджу 🙅")
            return
        challenge = random.choice(CHALLENGES)
        add_coins(uid, 5)
        await msg.answer(f"🎯 Твій челендж:\n\n{challenge}\n\n+5 🪙 нараховано!")
        return

    if text == "💌 Написати добро":
        if not is_active("добро"):
            await msg.answer("Сьогодні без доброти 🙅")
            return
        user_states[uid] = "good"
        await msg.answer("Напиши щось добре — хтось отримає анонімно 💌")
        return

    if text == "🎰 Удача":
        if not is_active("лотерея"):
            await msg.answer("Сьогодні лотерея не працює 🙅")
            return
        now = datetime.now(kyiv)
        week_key = now.strftime("%Y-W%W")
        plays = luck_log.get(uid, [])
        plays_this_week = [d for d in plays if d == week_key]
        if len(plays_this_week) >= 2:
            await msg.answer("🎰 Цього тижня ти вже зіграв 2 рази.\nПоверни наступного тижня! 🍀")
            return
        result = random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
        plays.append(week_key)
        luck_log[uid] = plays
        plays_left = 2 - len([d for d in plays if d == week_key])
        slots = ["🍋", "🍒", "🍇", "⭐️", "🔔", "💎"]
        s1, s2, s3 = random.choices(slots, k=3)
        if result > 0:
            add_coins(uid, result)
            await msg.answer(
                f"🎰 {s1} | {s2} | {s3}\n\n"
                f"🎉 Виграш! +{result} 🪙\n"
                f"Залишилось спроб цього тижня: {plays_left}"
            )
        else:
            await msg.answer(
                f"🎰 {s1} | {s2} | {s3}\n\n"
                f"😅 Не пощастило!\n"
                f"Залишилось спроб цього тижня: {plays_left}"
            )
        return

    if text == "😴 Я прокинувся":
        if wake_log.get(uid) == today_str():
            await msg.answer("Ти вже прокидався сьогодні 😄")
        else:
            wake_log[uid] = today_str()
            add_coins(uid, 3)
            await msg.answer("☀️ Доброго ранку! +3 🪙")
        return

    if text == "🪙 Мої монетки":
        c = get_coins(uid)
        await msg.answer(f"У тебе: {c} 🪙\nРівень: {get_level(c)}")
        return

    if text == "🏦 Банк класу":
        await msg.answer(f"Банк класу: {get_class_bank()} 🪙")
        return

    if text == "🏆 Рейтинг":
        users = get_all_users()
        ranked = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)
        txt = "🏆 ТОП класу:\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (tuid, info) in enumerate(ranked[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            display = ADMIN_DISPLAY.get(info["name"], info["name"])
            txt += f"{medal} {display} {get_level(info['coins'])} — {info['coins']} 🪙\n"
        await msg.answer(txt)
        return

    if text == "📬 Скарга":
        user_states[uid] = "complaint"
        await msg.answer("📬 Напиши скаргу — піде вчителю анонімно 🤫")
        return

    # Комплімент дня — відправка
    if user_states.get(uid, "").startswith("compliment_to:"):
        target_uid = user_states[uid].split(":")[1]
        try:
            await bot.send_message(int(target_uid), f"💌 Хтось написав тобі комплімент:\n\n{text} 🌸")
        except Exception:
            pass
        add_coins(uid, 2)
        user_states.pop(uid, None)
        await msg.answer("✅ Комплімент надіслано! +2 🪙 💌")
        return

    if text == "🎰 Удача" and not is_active("лотерея"):
        await msg.answer("Сьогодні лотерея не працює 🙅")
        return

    if text == "🎰 Удача":
        now = datetime.now(kyiv)
        week_key = now.strftime("%Y-W%W")
        plays = luck_log.get(uid, [])
        plays_this_week = [d for d in plays if d == week_key]
        if len(plays_this_week) >= 2:
            await msg.answer("🎰 Цього тижня ти вже зіграв 2 рази.\nПоверни наступного тижня! 🍀")
            return
        result = random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
        plays.append(week_key)
        luck_log[uid] = plays
        plays_left = 2 - len([d for d in plays if d == week_key])
        slots = ["🍋", "🍒", "🍇", "⭐️", "🔔", "💎"]
        s1, s2, s3 = random.choices(slots, k=3)
        if result > 0:
            add_coins(uid, result)
            await msg.answer(
                f"🎰 {s1} | {s2} | {s3}\n\n"
                f"🎉 Виграш! +{result} 🪙\n"
                f"Залишилось спроб цього тижня: {plays_left}"
            )
        else:
            await msg.answer(
                f"🎰 {s1} | {s2} | {s3}\n\n"
                f"😅 Не пощастило!\n"
                f"Залишилось спроб цього тижня: {plays_left}"
            )
        return

    if text == "🤫 Таємний друг":
        global secret_friend_pairs, secret_friend_cycle
        if not secret_friend_cycle:
            await msg.answer(
                "🤫 Таємний друг ще не призначений.\n"
                "Пари формуються автоматично кожні два тижні в понеділок!"
            )
            return
        friend_uid = secret_friend_pairs.get(uid)
        if not friend_uid:
            await msg.answer("🤫 Тобі ще не призначено таємного друга в цьому циклі.")
            return
        user_states[uid] = f"secret_msg:{friend_uid}"
        await msg.answer(
            "🤫 Твій таємний друг чекає на щось приємне!\n\n"
            "Напиши йому анонімне повідомлення 💌"
        )
        return

    # Таємне повідомлення другу
    if user_states.get(uid, "").startswith("secret_msg:"):
        friend_uid = user_states[uid].split(":")[1]
        try:
            await bot.send_message(int(friend_uid), f"🤫 Твій таємний друг написав:\n\n{text}")
        except Exception:
            pass
        add_coins(uid, 2)
        user_states.pop(uid, None)
        await msg.answer("✅ Надіслано таємному другу! +2 🪙 💌")
        return

    # ===== МАГАЗИН =====

    if text == "🛒 Магазин":
        c = get_coins(uid)
        txt = f"🛒 Магазин класу\nТвій баланс: {c} 🪙\n\n"
        for item in SHOP_ITEMS:
            price_text = f"{item['price']} 🪙" if item["price"] > 0 else "безкоштовно"
            txt += f"{item['emoji']} {item['name']} — {price_text}\n   {item['desc']}\n\n"
        await msg.answer(txt, reply_markup=shop_kb())
        return

    # Кнопки магазину
    for item in SHOP_ITEMS:
        price_text = f"{item['price']} 🪙" if item["price"] > 0 else "безкоштовно"
        if text == f"{item['emoji']} {item['name']} — {price_text}":
            if item["id"] == "gift":
                user_states[uid] = "shop_gift_who"
                await msg.answer("Введи @username того, кому хочеш подарувати монети:")
                return

            my_coins = get_coins(uid)
            if my_coins < item["price"]:
                await msg.answer(
                    f"❌ Не вистачає монет!\nПотрібно: {item['price']} 🪙\nУ тебе: {my_coins} 🪙\n\n"
                    f"💡 Можна скластися разом! Натисни 🧺 Спільні кошики"
                )
                return

            remove_coins_from(uid, item["price"])
            if purchases_sheet:
                purchases_sheet.append_row([now_str(), get_user_name(uid), item["name"], item["price"]])
            await notify_admin(
                f"🛒 Покупка!\nУчень: {get_user_name(uid)}\n"
                f"Товар: {item['emoji']} {item['name']}\nЦіна: {item['price']} 🪙"
            )
            await msg.answer(
                f"✅ Куплено: {item['emoji']} {item['name']}\n"
                f"Списано: {item['price']} 🪙\nВчитель вже знає! 👩‍🏫",
                reply_markup=build_main_kb(uid)
            )
            return

    # ===== СПІЛЬНІ КОШИКИ =====

    if text == "🧺 Спільні кошики":
        baskets = get_baskets()
        if not baskets:
            # показуємо список товарів для створення кошика
            txt = "🧺 Спільні кошики\n\nЗараз немає активних зборів.\nОбери товар щоб почати збір:\n\n"
            rows_kb = []
            for item in SHOP_ITEMS:
                if item["id"] != "gift" and item["price"] > 0:
                    rows_kb.append([KeyboardButton(text=f"🧺 Створити збір: {item['name']}")])
            rows_kb.append([KeyboardButton(text="🔙 Назад")])
            await msg.answer(txt, reply_markup=ReplyKeyboardMarkup(keyboard=rows_kb, resize_keyboard=True))
        else:
            txt = "🧺 Активні збори:\n\n"
            rows_kb = []
            for b in baskets:
                remaining = b["price"] - b["collected"]
                txt += f"{b['item_name']}: {b['collected']}/{b['price']} 🪙 (ще {remaining} 🪙)\n"
                rows_kb.append([KeyboardButton(text=f"➕ Внести в: {b['item_name']}")])
            rows_kb.append([KeyboardButton(text="🔙 Назад")])
            await msg.answer(txt, reply_markup=ReplyKeyboardMarkup(keyboard=rows_kb, resize_keyboard=True))
        return

    # Створити кошик
    if text.startswith("🧺 Створити збір: "):
        item_name = text.replace("🧺 Створити збір: ", "")
        item = next((i for i in SHOP_ITEMS if i["name"] == item_name), None)
        if not item:
            await msg.answer("Товар не знайдено.", reply_markup=build_main_kb(uid))
            return
        existing = find_basket(item["id"])
        if existing:
            await msg.answer(f"Збір на {item_name} вже існує!\nЗібрано: {existing['collected']}/{existing['price']} 🪙")
            return
        create_basket(item)
        user_states[uid] = f"basket_contribute:{item['id']}"
        await msg.answer(
            f"🧺 Збір на {item['emoji']} {item_name} створено!\n"
            f"Потрібно: {item['price']} 🪙\n\nСкільки вносиш зараз?"
        )
        return

    # Внести в кошик
    if text.startswith("➕ Внести в: "):
        item_name = text.replace("➕ Внести в: ", "")
        basket = next((b for b in get_baskets() if b["item_name"] == item_name), None)
        if not basket:
            await msg.answer("Збір не знайдено.", reply_markup=build_main_kb(uid))
            return
        user_states[uid] = f"basket_contribute:{basket['item_id']}"
        remaining = basket["price"] - basket["collected"]
        await msg.answer(
            f"🧺 {item_name}\nЗібрано: {basket['collected']}/{basket['price']} 🪙\n"
            f"Ще треба: {remaining} 🪙\n\nСкільки вносиш?"
        )
        return

    # ===== ВЧИТЕЛЬ =====

    if text == "⚖️ Дія вчителя":
        if not is_admin(uid):
            await msg.answer("Тільки для вчителя 🙅")
            return
        await msg.answer("Обери дію:", reply_markup=teacher_kb)
        return

    if text == "➕ Плюс учню" and is_admin(uid):
        user_states[uid] = "teacher_plus"
        await msg.answer("Формат: @username кількість")
        return

    if text == "➖ Мінус учню" and is_admin(uid):
        user_states[uid] = "teacher_minus"
        await msg.answer("Формат: @username кількість")
        return

    if text == "💸 Штраф класу" and is_admin(uid):
        user_states[uid] = "teacher_fine"
        await msg.answer(f"Банк зараз: {get_class_bank()} 🪙\nСкільки зняти?")
        return

    if text == "🕊️ Амністія" and is_admin(uid):
        for tuid in get_all_users():
            try: await bot.send_message(int(tuid), "🕊️ Вчитель оголосив амністію! 🎉")
            except Exception: pass
        await msg.answer("🕊️ Амністія оголошена!", reply_markup=teacher_kb)
        return

    if text == "🔙 Назад":
        user_states.pop(uid, None)
        await msg.answer("Головне меню 👇", reply_markup=build_main_kb(uid))
        return

# ================= АВТОЗАВДАННЯ =================

async def morning_digest():
    """О 7:45 надсилає ранковий дайджест з розкладом."""
    global gold_coin_log
    while True:
        now = datetime.now(kyiv)
        target = now.replace(hour=7, minute=45, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        now = datetime.now(kyiv)
        weekday = now.weekday()

        if weekday < 5:
            modes = get_active_modes()
            mode_names = {
                "мем":     "😂 Мем дня",
                "челендж": "🎯 Челендж дня",
                "добро":   "💌 Написати добро",
                "лотерея": "🎰 Удача",
            }
            active_text = "\n".join(f"• {mode_names[m]}" for m in modes)
            lessons = get_schedule_for_day(weekday)
            schedule_text = format_schedule(lessons, DAYS_UA[weekday])

            digest = (
                f"⏰ Доброго ранку!\n\n"
                f"{schedule_text}\n\n"
                f"🎮 Сьогодні активні:\n{active_text}\n\n"
                f"Натисни 😴 Я прокинувся — це +3 🪙!"
            )
        else:
            digest = "☀️ Доброго ранку! Сьогодні вихідний 🎉 Відпочивай!"

        users = get_all_users()

        # Перевірка іменинників
        today_ddmm = now.strftime("%d.%m")
        birthdays_today = []
        if holidays_sheet:
            try:
                rows = holidays_sheet.get_all_records()
                for r in rows:
                    if str(r.get("Дата", "")).strip() == today_ddmm:
                        surname = str(r.get("Прізвище", "")).strip()
                        firstname = str(r.get("Ім'я", "")).strip()
                        birthdays_today.append(f"{surname} {firstname}")
            except Exception:
                pass

        # Золота монета — раз на місяць
        current_month = now.strftime("%Y-%m")
        gold_msg = ""
        if gold_coin_log != current_month and users:
            gold_coin_log = current_month
            lucky_uid = random.choice(list(users.keys()))
            add_coins(lucky_uid, 50)
            gold_msg = f"\n\n🌟 Золота монета цього місяця — {get_user_name(lucky_uid)}! +50 🪙"

        # Факт дня — по індексу, не повторюється
        fact_index = int(get_bank_value("fact_index", "0"))
        if fact_index >= len(FACTS):
            fact_index = 0
            set_bank_value("fact_index", "0")
        fact_text = f"\n\n🔍 Цікавий факт:\n{FACTS[fact_index]}"
        set_bank_value("fact_index", str(fact_index + 1))

        # Попередження коли залишається 10 фактів
        remaining_facts = len(FACTS) - (fact_index + 1)
        if remaining_facts <= 10:
            await notify_admin(
                f"⚠️ Залишилось лише {remaining_facts} цікавих фактів!\n"
                f"Додай нові факти в список FACTS у коді боту 📝"
            )

        # Шлях до mp3
        alarm_path = os.path.join(os.path.dirname(__file__), "alarm.mp3.mp3")
        alarm_exists = os.path.exists(alarm_path)

        for tuid in users:
            try:
                if alarm_exists:
                    audio = FSInputFile(alarm_path)
                    await bot.send_audio(int(tuid), audio=audio, caption="⏰ Час прокидатись!")
                msg_text = digest + fact_text
                if gold_msg:
                    msg_text += gold_msg
                await bot.send_message(int(tuid), msg_text)
            except Exception:
                pass

        # Вітання іменинників
        if birthdays_today:
            for bday_name in birthdays_today:
                bday_msg = f"🎂 Сьогодні день народження у {bday_name}!\nВесь клас вітає! 🎉🎈"
                for tuid in users:
                    try: await bot.send_message(int(tuid), bday_msg)
                    except Exception: pass
                for tuid, info in users.items():
                    if info["name"].strip() == bday_name.strip():
                        add_coins(tuid, 10)
                        try: await bot.send_message(int(tuid), "🎁 +10 🪙 у подарунок на день народження!")
                        except Exception: pass

        await asyncio.sleep(60)

async def reset_wake_daily():
    """О 00:01 скидає позначки прокидань."""
    while True:
        now = datetime.now(kyiv)
        target = now.replace(hour=0, minute=1, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        wake_log.clear()

async def compliment_of_day():
    """Щопонеділка о 12:00 бот обирає 5 пар і просить написати компліменти."""
    global compliment_log
    while True:
        now = datetime.now(kyiv)
        target = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        now = datetime.now(kyiv)
        # тільки в понеділок
        if now.weekday() != 0:
            await asyncio.sleep(60)
            continue

        week_key = now.strftime("%Y-W%W")
        if compliment_log == week_key:
            await asyncio.sleep(60)
            continue
        compliment_log = week_key

        users = get_all_users()
        uids = list(users.keys())
        if len(uids) < 2:
            await asyncio.sleep(60)
            continue

        # 5 пар (або менше якщо учнів мало)
        random.shuffle(uids)
        pairs_count = min(5, len(uids) // 2)
        pairs = [(uids[i*2], uids[i*2+1]) for i in range(pairs_count)]

        for a, b in pairs:
            name_a = get_user_name(a)
            name_b = get_user_name(b)
            try:
                await bot.send_message(
                    int(a),
                    f"💌 Комплімент тижня!\n\nНапиши щось приємне для {name_b} 😊"
                )
                user_states[a] = f"compliment_to:{b}"
            except Exception:
                pass
            try:
                await bot.send_message(
                    int(b),
                    f"💌 Комплімент тижня!\n\nНапиши щось приємне для {name_a} 😊"
                )
                user_states[b] = f"compliment_to:{a}"
            except Exception:
                pass

        await asyncio.sleep(60)

async def secret_friend_task():
    """Кожні два тижні (в понеділок парного тижня) формує 3 пари таємних друзів."""
    global secret_friend_pairs, secret_friend_cycle
    while True:
        now = datetime.now(kyiv)
        target = now.replace(hour=8, minute=30, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        now = datetime.now(kyiv)
        # тільки в понеділок
        if now.weekday() != 0:
            await asyncio.sleep(60)
            continue

        # парний тиждень
        week_num = int(now.strftime("%W"))
        if week_num % 2 != 0:
            await asyncio.sleep(60)
            continue

        cycle_key = now.strftime("%Y-W%W")
        if secret_friend_cycle == cycle_key:
            await asyncio.sleep(60)
            continue
        secret_friend_cycle = cycle_key

        users = get_all_users()
        uids = list(users.keys())
        if len(uids) < 2:
            await asyncio.sleep(60)
            continue

        # 3 пари (6 учнів рандомно)
        random.shuffle(uids)
        pairs_count = min(3, len(uids) // 2)
        selected = uids[:pairs_count * 2]

        secret_friend_pairs = {}
        for i in range(0, len(selected), 2):
            a, b = selected[i], selected[i+1]
            secret_friend_pairs[a] = b
            secret_friend_pairs[b] = a

        for uid_sf in secret_friend_pairs:
            try:
                await bot.send_message(
                    int(uid_sf),
                    "🤫 Старт нового циклу Таємного друга!\n\n"
                    "Тобі призначено таємного друга на 2 тижні 💌\n"
                    "Натисни 🤫 Таємний друг щоб написати йому анонімно!"
                )
            except Exception:
                pass

        await asyncio.sleep(60)

# ================= MAIN =================

async def main():
    init_google()
    dp.include_router(router)
    asyncio.create_task(morning_digest())
    asyncio.create_task(reset_wake_daily())
    asyncio.create_task(compliment_of_day())
    asyncio.create_task(secret_friend_task())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
