"""Internationalisation: languages, per-language currency, and translations.

Prices are computed by the engine in TJS and converted to the user's currency
via :func:`money`. UI strings come from :func:`t` with graceful fallback to
Russian (then the key) so nothing ever crashes on a missing translation.

Translations for the smaller Central-Asian / Caucasus / Belarusian languages are
best-effort and easy to refine in one place (the ``STRINGS`` catalog).
"""

from __future__ import annotations

import datetime as _dt
from typing import Dict, List

DEFAULT_LANG = "ru"

# Ordered languages with native label + flag (used for the picker).
LANG_META: Dict[str, str] = {
    "ru": "🇷🇺 Русский",
    "tg": "🇹🇯 Тоҷикӣ",
    "uz": "🇺🇿 Oʻzbekcha",
    "ky": "🇰🇬 Кыргызча",
    "kk": "🇰🇿 Қазақша",
    "tk": "🇹🇲 Türkmençe",
    "az": "🇦🇿 Azərbaycanca",
    "be": "🇧🇾 Беларуская",
    "en": "🇬🇧 English",
}
LANGS: List[str] = list(LANG_META.keys())

# Currency per language.
CURRENCY: Dict[str, str] = {
    "ru": "RUB", "tg": "TJS", "uz": "UZS", "ky": "KGS", "kk": "KZT",
    "tk": "TMT", "az": "AZN", "be": "BYN", "en": "USD",
}

# Approximate FX: 1 TJS -> currency unit (engine base prices are in TJS).
FX: Dict[str, float] = {
    "TJS": 1.0, "RUB": 8.3, "UZS": 1180.0, "KGS": 8.0, "KZT": 48.0,
    "TMT": 0.33, "AZN": 0.155, "BYN": 0.30, "USD": 0.091,
}


def normalize(lang: str | None) -> str:
    return lang if lang in LANG_META else DEFAULT_LANG


def currency_of(lang: str) -> str:
    return CURRENCY.get(normalize(lang), "TJS")


def money(lang: str, tjs_amount: int) -> str:
    cur = currency_of(lang)
    amount = int(round(tjs_amount * FX.get(cur, 1.0)))
    return f"{amount:,}".replace(",", "\u00a0") + f" {cur}"


# --- dates -----------------------------------------------------------------

_RU_MONTHS = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
_EN_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(lang: str, date: _dt.date) -> str:
    lang = normalize(lang)
    if lang == "ru":
        return f"{date.day} {_RU_MONTHS[date.month]}"
    if lang == "en":
        return f"{date.day} {_EN_MONTHS[date.month]}"
    return f"{date.day:02d}.{date.month:02d}"


def fmt_dt(lang: str, value: _dt.datetime) -> str:
    return f"{fmt_date(lang, value.date())} {value:%H:%M}"


# --- string catalog --------------------------------------------------------
# Each key maps lang -> template. Missing langs fall back to "ru", then the key.

STRINGS: Dict[str, Dict[str, str]] = {
    "welcome": {
        "ru": "✈️ *AviaBot* — поиск и отслеживание авиабилетов.\nНажмите 🔎 Поиск, чтобы начать, или /help.",
        "tg": "✈️ *AviaBot* — ҷустуҷӯ ва пайгирии чиптаҳои ҳавопаймо.\nБарои оғоз 🔎 Ҷустуҷӯ-ро пахш кунед ё /help.",
        "uz": "✈️ *AviaBot* — aviachiptalarni qidirish va kuzatish.\nBoshlash uchun 🔎 Qidiruv tugmasini bosing yoki /help.",
        "ky": "✈️ *AviaBot* — авиабилеттерди издөө жана байкоо.\nБаштоо үчүн 🔎 Издөө басыңыз же /help.",
        "kk": "✈️ *AviaBot* — авиабилеттерді іздеу және бақылау.\nБастау үшін 🔎 Іздеу түймесін басыңыз немесе /help.",
        "tk": "✈️ *AviaBot* — awiabiletleri gözlemek we yzarlamak.\nBaşlamak üçin 🔎 Gözleg basyň ýa-da /help.",
        "az": "✈️ *AviaBot* — aviabiletlərin axtarışı və izlənməsi.\nBaşlamaq üçün 🔎 Axtarış düyməsini basın və ya /help.",
        "be": "✈️ *AviaBot* — пошук і адсочванне авіябілетаў.\nНацісніце 🔎 Пошук, каб пачаць, або /help.",
        "en": "✈️ *AviaBot* — flight search & price tracking.\nTap 🔎 Search to begin, or /help.",
    },
    "help": {
        "ru": "🔎 Поиск — пошагово. 🔎🗓 По диапазону — дешёвый день. 👀 Отслеживание цены. 🔥 /hot. 🗂 /mytracks. 🌐 /language.",
        "en": "🔎 Search — step by step. 🔎🗓 Range — cheapest day. 👀 Price tracking. 🔥 /hot. 🗂 /mytracks. 🌐 /language.",
        "uz": "🔎 Qidiruv — bosqichma-bosqich. 🔎🗓 Diapazon — arzon kun. 👀 Narx kuzatuvi. 🔥 /hot. 🗂 /mytracks. 🌐 /language.",
        "tg": "🔎 Ҷустуҷӯ — қадам ба қадам. 🔎🗓 Фосила — рӯзи арзон. 👀 Пайгирии нарх. 🔥 /hot. 🗂 /mytracks. 🌐 /language.",
    },
    "ask_from": {
        "ru": "🏠 Введите город откуда летите (Пример: Москва)",
        "tg": "🏠 Шаҳри парвозро ворид кунед (Мисол: Москва)",
        "uz": "🏠 Uchib chiqadigan shaharni kiriting (Masalan: Moskva)",
        "ky": "🏠 Учуп чыккан шаарды жазыңыз (Мисалы: Москва)",
        "kk": "🏠 Ұшатын қаланы енгізіңіз (Мысалы: Мәскеу)",
        "tk": "🏠 Ugraýan şäheriňizi ýazyň (Mysal: Moskwa)",
        "az": "🏠 Uçduğunuz şəhəri yazın (Məsələn: Moskva)",
        "be": "🏠 Увядзіце горад адкуль ляціце (Прыклад: Масква)",
        "en": "🏠 Enter departure city (e.g. Moscow)",
    },
    "choose_from": {
        "ru": "Выберите из списка откуда отправляетесь",
        "tg": "Аз рӯйхат интихоб кунед, ки аз куҷо парвоз мекунед",
        "uz": "Roʻyxatdan qayerdan uchishingizni tanlang",
        "ky": "Тизмеден кайдан учаарыңызды тандаңыз",
        "kk": "Тізімнен қайдан ұшатыныңызды таңдаңыз",
        "tk": "Sanawdan nireden ugraýanyňyzy saýlaň",
        "az": "Siyahıdan haradan uçduğunuzu seçin",
        "be": "Выберыце са спісу адкуль вылятаеце",
        "en": "Choose your departure from the list",
    },
    "ask_to": {
        "ru": "🛫 Введите город куда вы летите (Пример: Худжанд)",
        "tg": "🛫 Шаҳри мақсадро ворид кунед (Мисол: Хуҷанд)",
        "uz": "🛫 Qayerga uchishingizni kiriting (Masalan: Xoʻjand)",
        "ky": "🛫 Кайда учаарыңызды жазыңыз (Мисалы: Хужанд)",
        "kk": "🛫 Қайда ұшатыныңызды енгізіңіз (Мысалы: Хожанд)",
        "tk": "🛫 Nirä barýanyňyzy ýazyň (Mysal: Hojent)",
        "az": "🛫 Hara uçduğunuzu yazın (Məsələn: Xocənd)",
        "be": "🛫 Увядзіце горад куды ляціце (Прыклад: Худжанд)",
        "en": "🛫 Enter destination city (e.g. Khujand)",
    },
    "choose_to": {
        "ru": "Выберите из списка куда летите",
        "uz": "Roʻyxatdan qayerga uchishingizni tanlang",
        "tg": "Аз рӯйхат интихоб кунед, ки ба куҷо парвоз мекунед",
        "en": "Choose your destination from the list",
    },
    "city_not_found": {
        "ru": "Не нашёл такой город. Попробуйте ещё раз (например: Москва, Ташкент).",
        "uz": "Bunday shahar topilmadi. Qayta urinib koʻring (masalan: Moskva, Toshkent).",
        "tg": "Чунин шаҳр ёфт нашуд. Аз нав кӯшиш кунед (масалан: Москва, Тошканд).",
        "en": "City not found. Try again (e.g. Moscow, Tashkent).",
    },
    "pax_prompt": {
        "ru": "Выберите кол-во пассажиров и класс",
        "tg": "Шумораи мусофирон ва синфро интихоб кунед",
        "uz": "Yoʻlovchilar sonini va sinfni tanlang",
        "ky": "Жүргүнчүлөрдүн санын жана классын тандаңыз",
        "kk": "Жолаушылар санын және сыныпты таңдаңыз",
        "tk": "Ýolagçy sanyny we synpy saýlaň",
        "az": "Sərnişin sayını və sinfi seçin",
        "be": "Выберыце колькасць пасажыраў і клас",
        "en": "Choose passengers and cabin class",
    },
    "adults": {"ru": "Взрослые", "uz": "Kattalar", "tg": "Калонсолон", "ky": "Чоңдор",
               "kk": "Ересектер", "tk": "Ulular", "az": "Böyüklər", "be": "Дарослыя", "en": "Adults"},
    "children": {"ru": "Дети", "uz": "Bolalar", "tg": "Кӯдакон", "ky": "Балдар",
                 "kk": "Балалар", "tk": "Çagalar", "az": "Uşaqlar", "be": "Дзеці", "en": "Children"},
    "infants": {"ru": "Младенцы", "uz": "Chaqaloqlar", "tg": "Навзодон", "ky": "Ымыркайлар",
                "kk": "Нәрестелер", "tk": "Bäbekler", "az": "Körpələr", "be": "Немаўляты", "en": "Infants"},
    "economy": {"ru": "Эконом", "uz": "Ekonom", "tg": "Эконом", "ky": "Эконом", "kk": "Эконом",
                "tk": "Ekonom", "az": "Ekonom", "be": "Эканом", "en": "Economy"},
    "business": {"ru": "Бизнес", "uz": "Biznes", "tg": "Бизнес", "ky": "Бизнес", "kk": "Бизнес",
                 "tk": "Biznes", "az": "Biznes", "be": "Бізнес", "en": "Business"},
    "ab_adult": {"ru": "взр.", "uz": "kat.", "tg": "калон.", "en": "ad."},
    "ab_child": {"ru": "дет.", "uz": "bol.", "tg": "кӯд.", "en": "ch."},
    "ab_infant": {"ru": "млад.", "uz": "chaq.", "tg": "навз.", "en": "inf."},
    "dates_hint": {
        "ru": "🗓 Выберите день вылета и обратно (если нужно).",
        "uz": "🗓 Uchish va (kerak boʻlsa) qaytish kunini tanlang.",
        "tg": "🗓 Рӯзи парвоз ва бозгаштро (агар лозим) интихоб кунед.",
        "en": "🗓 Pick the outbound and (optional) return date.",
    },
    "label_depart": {"ru": "🚀 Вылет", "uz": "🚀 Uchish", "tg": "🚀 Парвоз", "en": "🚀 Depart"},
    "label_return": {"ru": "🔄 Обратно", "uz": "🔄 Qaytish", "tg": "🔄 Бозгашт", "en": "🔄 Return"},
    "searching": {
        "ru": "Ищу на {p}…", "uz": "{p} da qidiryapman…", "tg": "Дар {p} меҷӯям…",
        "en": "Searching {p}…",
    },
    "tag_fastest": {"ru": "🔴 Самый быстрый 🏎", "uz": "🔴 Eng tez 🏎", "tg": "🔴 Тезтарин 🏎",
                    "en": "🔴 Fastest 🏎"},
    "tag_cheapest": {"ru": "🟢 Самый дешёвый 💸", "uz": "🟢 Eng arzon 💸", "tg": "🟢 Арзонтарин 💸",
                     "en": "🟢 Cheapest 💸"},
    "direct": {"ru": "Прямой", "uz": "Toʻgʻridan-toʻgʻri", "tg": "Мустақим", "ky": "Түз",
               "kk": "Тікелей", "tk": "Göni", "az": "Birbaşa", "be": "Прамы", "en": "Direct"},
    "transfers": {  # {n} {info}
        "ru": "🔀 {n} пересадка: {info}", "uz": "🔀 {n} transfer: {info}",
        "tg": "🔀 {n} истгоҳ: {info}", "en": "🔀 {n} stop(s): {info}",
    },
    "bag_yes": {"ru": "🧳 С багажом", "uz": "🧳 Bagaj bilan", "tg": "🧳 Бо бор", "en": "🧳 With baggage"},
    "bag_no": {"ru": "🎒 Без багажа", "uz": "🎒 Bagajsiz", "tg": "🎒 Бе бор", "en": "🎒 No baggage"},
    "leg_there": {"ru": "— Туда:", "uz": "— Boradigan:", "tg": "— Рафтан:", "en": "— Outbound:"},
    "per_adult": {"ru": "{m}/взр.", "uz": "{m}/kat.", "tg": "{m}/калон.", "en": "{m}/adult"},
    "btn_done": {"ru": "✅ Готово", "uz": "✅ Tayyor", "tg": "✅ Тайёр", "en": "✅ Done"},
    "btn_go": {"ru": "✅ Далее", "uz": "✅ Keyingi", "tg": "✅ Оянда", "ky": "✅ Кийинки",
               "kk": "✅ Келесі", "tk": "✅ Indiki", "az": "✅ Növbəti", "be": "✅ Далей", "en": "✅ Next"},
    "btn_buy": {"ru": "Купить билет", "uz": "Chipta sotib olish", "tg": "Харидани чипта",
                "ky": "Билет сатып алуу", "kk": "Билет сатып алу", "tk": "Bilet satyn al",
                "az": "Bilet al", "be": "Купіць білет", "en": "Buy ticket"},
    "seats_left": {"ru": "Осталось", "uz": "Qoldi", "tg": "Боқӣ монд", "en": "Left"},
    "btn_filters": {"ru": "⚙️ Фильтры", "uz": "⚙️ Filtrlar", "tg": "⚙️ Филтрҳо", "en": "⚙️ Filters"},
    "btn_refresh": {"ru": "🔄 Обновить", "uz": "🔄 Yangilash", "tg": "🔄 Навсозӣ", "en": "🔄 Refresh"},
    "btn_flex": {"ru": "🗓 ±3 дня", "uz": "🗓 ±3 kun", "tg": "🗓 ±3 рӯз", "en": "🗓 ±3 days"},
    "btn_track": {"ru": "➕👀 Отслеживать цену", "uz": "➕👀 Narxni kuzatish", "tg": "➕👀 Пайгирии нарх",
                  "en": "➕👀 Track price"},
    "flt_direct": {"ru": "Только прямые", "uz": "Faqat toʻgʻri", "tg": "Танҳо мустақим", "en": "Direct only"},
    "flt_bag": {"ru": "С багажом", "uz": "Bagaj bilan", "tg": "Бо бор", "en": "With baggage"},
    "flt_apply": {"ru": "Применить", "uz": "Qoʻllash", "tg": "Татбиқ", "en": "Apply"},
    "flt_reset": {"ru": "Сбросить", "uz": "Tozalash", "tg": "Тоза кардан", "en": "Reset"},
    "flt_title": {"ru": "⚙️ Фильтры поиска:", "uz": "⚙️ Qidiruv filtrlari:", "tg": "⚙️ Филтрҳои ҷустуҷӯ:",
                  "en": "⚙️ Search filters:"},
    "kb_search": {"ru": "🔎 Поиск", "uz": "🔎 Qidiruv", "tg": "🔎 Ҷустуҷӯ", "ky": "🔎 Издөө",
                  "kk": "🔎 Іздеу", "tk": "🔎 Gözleg", "az": "🔎 Axtarış", "be": "🔎 Пошук", "en": "🔎 Search"},
    "kb_range": {"ru": "🔎🗓 По диапазону", "uz": "🔎🗓 Diapazon boʻyicha", "tg": "🔎🗓 Аз рӯи фосила",
                 "en": "🔎🗓 By date range"},
    "kb_track": {"ru": "➕👀 Добавить отслеживание", "uz": "➕👀 Kuzatuv qoʻshish",
                 "tg": "➕👀 Илова кардани пайгирӣ", "en": "➕👀 Add tracking"},
    "kb_lang": {"ru": "🌐 Язык", "uz": "🌐 Til", "tg": "🌐 Забон", "ky": "🌐 Тил", "kk": "🌐 Тіл",
                "tk": "🌐 Dil", "az": "🌐 Dil", "be": "🌐 Мова", "en": "🌐 Language"},
    "variant": {"ru": "Вариант {i} из {n}", "uz": "{i}-variant / {n}", "tg": "Вариант {i} аз {n}",
                "en": "Option {i} of {n}"},
    "filters_label": {"ru": "⚙️ Фильтры: {f}", "uz": "⚙️ Filtrlar: {f}", "tg": "⚙️ Филтрҳо: {f}",
                      "en": "⚙️ Filters: {f}"},
    "advice_down": {"ru": "💡 Совет: цена снижается — можно подождать или включить отслеживание.",
                    "uz": "💡 Maslahat: narx tushmoqda — kutib turing yoki kuzatuvni yoqing.",
                    "tg": "💡 Маслиҳат: нарх паст мешавад — интизор шавед ё пайгириро фаъол кунед.",
                    "en": "💡 Tip: price is falling — you may wait or enable tracking."},
    "advice_up": {"ru": "💡 Совет: цена растёт — брать выгоднее сейчас.",
                  "uz": "💡 Maslahat: narx oshmoqda — hozir olgan maʼqul.",
                  "tg": "💡 Маслиҳат: нарх боло меравад — ҳозир харидан беҳтар аст.",
                  "en": "💡 Tip: price is rising — better to buy now."},
    "flex_line": {"ru": "📅 Гибкие даты: дешевле всего *{d}* — {m}.",
                  "uz": "📅 Moslashuvchan sanalar: eng arzoni *{d}* — {m}.",
                  "tg": "📅 Санаҳои чандир: арзонтарин *{d}* — {m}.",
                  "en": "📅 Flexible dates: cheapest on *{d}* — {m}."},
    "flex_none": {"ru": "Рядом дешевле не нашлось.", "uz": "Yaqin kunlarda arzonrogʻi topilmadi.",
                  "tg": "Дар наздикӣ арзонтар ёфт нашуд.", "en": "No cheaper nearby date found."},
    "range_title": {"ru": "📅 {o} → {d}, {start} — {end} · {pax}:",
                    "en": "📅 {o} → {d}, {start} — {end} · {pax}:"},
    "cheapest_day": {"ru": "Дешевле всего — *{d}* за *{m}*.",
                     "uz": "Eng arzoni — *{d}*, {m}.",
                     "tg": "Арзонтарин — *{d}*, {m}.",
                     "en": "Cheapest — *{d}* at *{m}*."},
    "mark_cheapest": {"ru": "самый дешёвый", "uz": "eng arzon", "tg": "арзонтарин", "en": "cheapest"},
    "hot_title": {"ru": "🔥 *Горящие билеты* (макс. скидка сейчас):",
                  "uz": "🔥 *Chaqnab turgan chiptalar* (hozirgi eng katta chegirma):",
                  "tg": "🔥 *Чиптаҳои сӯзон* (тахфифи ҳозира):",
                  "en": "🔥 *Hot deals* (biggest discount now):"},
    "hot_none": {"ru": "Сейчас нет заметных скидок — загляните позже. 🙂",
                 "en": "No notable discounts now — check back later. 🙂"},
    "track_added": {"ru": "👀 Отслеживаю цену:\n📍 {o} → {d}, {date} · {pax}\n💰 Сейчас: *{m}*\n\nСообщу, как только цена упадёт. /mytracks — список.",
                    "uz": "👀 Narxni kuzatyapman:\n📍 {o} → {d}, {date} · {pax}\n💰 Hozir: *{m}*\n\nNarx tushishi bilan xabar beraman. /mytracks — roʻyxat.",
                    "tg": "👀 Нархро пайгирӣ мекунам:\n📍 {o} → {d}, {date} · {pax}\n💰 Ҳозир: *{m}*\n\nҲамин ки нарх паст шавад, хабар медиҳам. /mytracks — рӯйхат.",
                    "en": "👀 Tracking price:\n📍 {o} → {d}, {date} · {pax}\n💰 Now: *{m}*\n\nI'll alert you when it drops. /mytracks — list."},
    "drop": {"ru": "🔥 Цена упала! {o} → {d}, {date}\nБыло {prev} → стало *{new}* (−{pct}%).",
             "uz": "🔥 Narx tushdi! {o} → {d}, {date}\n{prev} edi → *{new}* boʻldi (−{pct}%).",
             "tg": "🔥 Нарх паст шуд! {o} → {d}, {date}\n{prev} буд → *{new}* шуд (−{pct}%).",
             "en": "🔥 Price dropped! {o} → {d}, {date}\nWas {prev} → now *{new}* (−{pct}%)."},
    "mytracks_title": {"ru": "👀 *Ваши отслеживания:*", "uz": "👀 *Kuzatuvlaringiz:*",
                       "tg": "👀 *Пайгириҳои шумо:*", "en": "👀 *Your tracked routes:*"},
    "mytracks_empty": {"ru": "У вас нет отслеживаний. Нажмите «➕👀 Добавить отслеживание» после поиска.",
                       "uz": "Kuzatuvlar yoʻq. Qidiruvdan soʻng «➕👀 Kuzatuv qoʻshish» ni bosing.",
                       "tg": "Пайгирӣ надоред. Пас аз ҷустуҷӯ «➕👀» -ро пахш кунед.",
                       "en": "No tracked routes yet. Tap «➕👀 Add tracking» after a search."},
    "tr_now": {"ru": "сейчас", "uz": "hozir", "tg": "ҳозир", "en": "now"},
    "tr_min": {"ru": "мин", "uz": "min", "tg": "мин", "en": "min"},
    "tr_checks": {"ru": "пров.", "uz": "tekshiruv", "tg": "санҷиш", "en": "checks"},
    "cancel": {"ru": "Отменил. Нажмите 🔎 Поиск, чтобы начать заново.",
               "uz": "Bekor qilindi. Qaytadan boshlash uchun 🔎 Qidiruv.",
               "tg": "Бекор шуд. Барои аз нав оғоз 🔎 Ҷустуҷӯ.",
               "en": "Cancelled. Tap 🔎 Search to start again."},
    "choose_language": {"ru": "🌐 Выберите язык (валюта подберётся автоматически):",
                        "uz": "🌐 Tilni tanlang (valyuta avtomatik tanlanadi):",
                        "tg": "🌐 Забонро интихоб кунед (асъор худкор интихоб мешавад):",
                        "en": "🌐 Choose a language (currency is set automatically):"},
    "language_set": {"ru": "Готово! Язык: {lang}, валюта: {cur}.",
                     "uz": "Tayyor! Til: {lang}, valyuta: {cur}.",
                     "tg": "Тайёр! Забон: {lang}, асъор: {cur}.",
                     "en": "Done! Language: {lang}, currency: {cur}."},
    "no_results": {"ru": "На эту дату рейсов не нашлось. Попробуйте другую дату или город.",
                   "uz": "Bu sanaga reyslar topilmadi. Boshqa sana yoki shaharni sinang.",
                   "tg": "Барои ин сана парвоз нест. Санаи дигар ё шаҳри дигарро кӯшиш кунед.",
                   "en": "No flights on this date. Try another date or city."},
    "no_results_filters": {"ru": "По этим фильтрам рейсов нет. Смягчите условия в «Фильтрах».",
                           "uz": "Bu filtrlar boʻyicha reys yoʻq. «Filtrlar» da shartlarni yumshating.",
                           "tg": "Бо ин филтрҳо парвоз нест. Шартҳоро дар «Филтрҳо» нарм кунед.",
                           "en": "No flights for these filters. Relax them in «Filters»."},
    "pick_date_alert": {"ru": "Выберите дату вылета", "uz": "Uchish sanasini tanlang",
                        "tg": "Санаи парвозро интихоб кунед", "en": "Pick a departure date"},
    "start_search_first": {"ru": "Сначала выполните поиск 🔎.", "uz": "Avval 🔎 qidiruvni bajaring.",
                           "tg": "Аввал ҷустуҷӯ 🔎 кунед.", "en": "Do a search 🔎 first."},
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = normalize(lang)
    entry = STRINGS.get(key, {})
    template = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    return template.format(**kwargs) if kwargs else template


def language_label(lang: str) -> str:
    return LANG_META.get(normalize(lang), lang)
