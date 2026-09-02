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


SYMBOLS = {
    "RUB": "₽", "USD": "$", "TJS": "TJS", "UZS": "soʻm", "KGS": "сом",
    "KZT": "₸", "TMT": "TMT", "AZN": "₼", "BYN": "Br",
}


def money(lang: str, tjs_amount: int) -> str:
    cur = currency_of(lang)
    amount = int(round(tjs_amount * FX.get(cur, 1.0)))
    pretty = f"{amount:,}".replace(",", "\u00a0")
    return f"{pretty} {SYMBOLS.get(cur, cur)}"


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


_RU_MONTHS_SHORT = ["", "янв", "фев", "мар", "апр", "мая", "июн",
                    "июл", "авг", "сен", "окт", "ноя", "дек"]
_RU_WDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
_EN_WDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def fmt_date_short(lang: str, date: _dt.date) -> str:
    lang = normalize(lang)
    if lang == "en":
        return f"{_EN_WDAYS[date.weekday()]}, {date.day} {_EN_MONTHS[date.month]}"
    return f"{_RU_WDAYS[date.weekday()]}, {date.day} {_RU_MONTHS_SHORT[date.month]}"


def fmt_time(value: _dt.datetime) -> str:
    return f"{value:%H:%M}"


# --- string catalog --------------------------------------------------------
# Each key maps lang -> template. Missing langs fall back to "ru", then the key.

STRINGS: Dict[str, Dict[str, str]] = {
    "welcome": {
        "ru": "AviaBot\nБилеты и цены — коротко и по делу.\n\nВыберите, что нужно ↓",
        "tg": "AviaBot\nЧиптаҳо ва нархҳо — кӯтоҳ ва равшан.\n\nИнтихоб кунед ↓",
        "uz": "AviaBot\nChiptalar va narxlar — qisqa va tushunarli.\n\nKeragini tanlang ↓",
        "ky": "AviaBot\nБилеттер жана баалар.\n\nТандаңыз ↓",
        "kk": "AviaBot\nБилеттер мен бағалар.\n\nТаңдаңыз ↓",
        "tk": "AviaBot\nBiletler we bahalar.\n\nSaýlaň ↓",
        "az": "AviaBot\nBiletlər və qiymətlər.\n\nSeçin ↓",
        "be": "AviaBot\nКвіткі і цэны — коратка.\n\nАбярыце ↓",
        "en": "AviaBot\nFlights and fares, without the noise.\n\nPick what you need ↓",
    },
    "help": {
        "ru": "Найти билеты — пошаговый поиск.\nКуда улететь дешево — идеи направлений.\nКалендарь цен — лучший день месяца.\nМои алерты — падение цены.\nКабинет — язык, валюта, история.\n\nГород, страну, аэропорт или код (LED) можно вводить как есть.",
        "en": "Find tickets — guided search.\nWhere to fly cheap — destination ideas.\nPrice calendar — best day of the month.\nAlerts — price drops.\nCabinet — language, currency, history.\n\nType a city, country, airport or code (LED).",
        "uz": "Chipta qidirish — bosqichma-bosqich.\nArzon yoʻnalishlar — gʻoyalar.\nNarx kalendari — oyning eng arzon kuni.\nAlertlar — narx tushishi.\nKabinet — til, valyuta, tarix.",
        "tg": "Ҷустуҷӯи чипта — қадам ба қадам.\nСафарҳои арзон — ғояҳо.\nТақвими нарх — рӯзи арзон.\nОгоҳӣ — паст шудани нарх.\nКабинет — забон, асъор, таърих.",
    },
    "ask_from": {
        "ru": "Откуда летите?\nГород, страна, аэропорт или код — например Москва, Россия, Шереметьево, SVO",
        "tg": "Аз куҷо парвоз?\nШаҳр, кишвар, фурудгоҳ ё код — масалан Москва, SVO",
        "uz": "Qayerdan uchasiz?\nShahar, mamlakat, aeroport yoki kod — masalan Moskva, SVO",
        "en": "Where from?\nCity, country, airport or code — e.g. Moscow, Russia, Sheremetyevo, SVO",
        "ky": "Кайдан учасыз? Шаар, өлкө же код (SVO).",
        "kk": "Қайдан ұшасыз? Қала, ел немесе код (SVO).",
        "tk": "Nireden? Şäher, ýurt ýa-da kod (SVO).",
        "az": "Haradan? Şəhər, ölkə və ya kod (SVO).",
        "be": "Адкуль ляціце? Горад, краіна або код (SVO).",
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
        "ru": "Куда летите?\nТоже город, страна, аэропорт или код",
        "tg": "Ба куҷо парвоз?",
        "uz": "Qayerga uchasiz?",
        "en": "Where to?\nCity, country, airport or code",
        "ky": "Кайда учасыз?", "kk": "Қайда ұшасыз?", "tk": "Nirä?",
        "az": "Hara?", "be": "Куды ляціце?",
    },
    "choose_to": {
        "ru": "Выберите из списка куда летите",
        "uz": "Roʻyxatdan qayerga uchishingizni tanlang",
        "tg": "Аз рӯйхат интихоб кунед, ки ба куҷо парвоз мекунед",
        "en": "Choose your destination from the list",
    },
    "city_not_found": {
        "ru": "Ничего не нашёл. Попробуйте иначе: Москва, Турция, Хитроу или LED.",
        "uz": "Topilmadi. Moskva, Turkiya, Heathrow yoki LED deb yozing.",
        "tg": "Ёфт нашуд. Москва, Туркия, LED-ро кӯшиш кунед.",
        "en": "Nothing found. Try a city, country, airport name or code (LED).",
    },
    "pax_prompt": {
        "ru": "Пассажиры и класс",
        "tg": "Мусофирон ва синф",
        "uz": "Yoʻlovchilar va sinf",
        "ky": "Жүргүнчүлөр жана класс",
        "kk": "Жолаушылар және сынып",
        "tk": "Ýolagçylar we synp",
        "az": "Sərnişinlər və sinif",
        "be": "Пасажыры і клас",
        "en": "Passengers and cabin",
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
        "ru": "Дата вылета",
        "uz": "Uchish sanasi",
        "tg": "Санаи парвоз",
        "en": "Departure date",
    },
    "label_depart": {"ru": "Туда", "uz": "Borish", "tg": "Рафтан", "en": "Outbound"},
    "label_return": {"ru": "Обратно", "uz": "Qaytish", "tg": "Бозгашт", "en": "Return"},
    "searching": {
        "ru": "Ищу на {p}…", "uz": "{p} da qidiryapman…", "tg": "Дар {p} меҷӯям…",
        "en": "Searching {p}…",
    },
    "tag_fastest": {"ru": "самый быстрый", "uz": "eng tez", "tg": "тезтарин",
                    "en": "fastest"},
    "tag_cheapest": {"ru": "самый дешёвый", "uz": "eng arzon", "tg": "арзонтарин",
                     "en": "cheapest"},
    "direct": {"ru": "Прямой", "uz": "Toʻgʻridan-toʻgʻri", "tg": "Мустақим", "ky": "Түз",
               "kk": "Тікелей", "tk": "Göni", "az": "Birbaşa", "be": "Прамы", "en": "Direct"},
    "stops_n": {"ru": "{n} пересадка", "uz": "{n} transfer", "tg": "{n} истгоҳ", "en": "{n} stop(s)"},
    "bag_yes": {"ru": "🧳 С багажом", "uz": "🧳 Bagaj bilan", "tg": "🧳 Бо бор", "en": "🧳 With baggage"},
    "bag_no": {"ru": "🎒 Без багажа", "uz": "🎒 Bagajsiz", "tg": "🎒 Бе бор", "en": "🎒 No baggage"},
    "leg_there": {"ru": "— Туда:", "uz": "— Boradigan:", "tg": "— Рафтан:", "en": "— Outbound:"},
    "per_adult": {"ru": "{m}/взр.", "uz": "{m}/kat.", "tg": "{m}/калон.", "en": "{m}/adult"},
    "btn_done": {"ru": "✅ Готово", "uz": "✅ Tayyor", "tg": "✅ Тайёр", "en": "✅ Done"},
    "btn_go": {"ru": "✅ Далее", "uz": "✅ Keyingi", "tg": "✅ Оянда", "ky": "✅ Кийинки",
               "kk": "✅ Келесі", "tk": "✅ Indiki", "az": "✅ Növbəti", "be": "✅ Далей", "en": "✅ Next"},
    "btn_buy": {"ru": "Забронировать", "uz": "Bron qilish", "tg": "Брон кардан",
                "ky": "Брондоо", "kk": "Брондау", "tk": "Bron et",
                "az": "Rezerv", "be": "Забраніраваць", "en": "Book"},
    "seats_left": {"ru": "Осталось", "uz": "Qoldi", "tg": "Боқӣ монд", "en": "Left"},
    "btn_filters": {"ru": "⚙️ Фильтры", "uz": "⚙️ Filtrlar", "tg": "⚙️ Филтрҳо", "en": "⚙️ Filters"},
    "btn_refresh": {"ru": "🔄 Обновить", "uz": "🔄 Yangilash", "tg": "🔄 Навсозӣ", "en": "🔄 Refresh"},
    "btn_flex": {"ru": "🗓 ±3 дня", "uz": "🗓 ±3 kun", "tg": "🗓 ±3 рӯз", "en": "🗓 ±3 days"},
    "btn_track": {"ru": "Отслеживать", "uz": "Kuzatish", "tg": "Пайгирӣ",
                  "en": "Track"},
    "btn_new_search": {"ru": "Новый поиск", "uz": "Yangi qidiruv", "tg": "Ҷустуҷӯи нав",
                       "en": "New search"},
    "flt_direct": {"ru": "Только прямые", "uz": "Faqat toʻgʻri", "tg": "Танҳо мустақим", "en": "Direct only"},
    "flt_bag": {"ru": "С багажом", "uz": "Bagaj bilan", "tg": "Бо бор", "en": "With baggage"},
    "flt_apply": {"ru": "Применить", "uz": "Qoʻllash", "tg": "Татбиқ", "en": "Apply"},
    "flt_reset": {"ru": "Сбросить", "uz": "Tozalash", "tg": "Тоза кардан", "en": "Reset"},
    "flt_title": {"ru": "⚙️ Фильтры поиска:", "uz": "⚙️ Qidiruv filtrlari:", "tg": "⚙️ Филтрҳои ҷустуҷӯ:",
                  "en": "⚙️ Search filters:"},
    "kb_search": {"ru": "Найти билеты", "uz": "Chipta qidirish", "tg": "Ҷустуҷӯи чипта",
                  "ky": "Билет издөө", "kk": "Билет іздеу", "tk": "Bilet gözle",
                  "az": "Bilet axtar", "be": "Знайсці квіткі", "en": "Find tickets"},
    "kb_discover": {"ru": "Куда улететь дешево", "uz": "Arzon yoʻnalishlar",
                    "tg": "Сафарҳои арзон", "en": "Where to fly cheap"},
    "kb_alerts": {"ru": "Мои алерты", "uz": "Alertlarim", "tg": "Огоҳиҳои ман",
                  "en": "My alerts"},
    "kb_calendar": {"ru": "Календарь цен", "uz": "Narx kalendari", "tg": "Тақвими нарх",
                    "en": "Price calendar"},
    "kb_cabinet": {"ru": "Кабинет", "uz": "Kabinet", "tg": "Кабинет", "en": "Account"},
    "kb_premium": {"ru": "Подписка", "uz": "Obuna", "tg": "Обуна", "en": "Premium"},
    "kb_lang": {"ru": "Язык", "uz": "Til", "tg": "Забон", "ky": "Тил", "kk": "Тіл",
                "tk": "Dil", "az": "Dil", "be": "Мова", "en": "Language"},
    "kb_help": {"ru": "Помощь", "uz": "Yordam", "tg": "Кӯмак", "en": "Help"},
    "kb_range": {"ru": "Календарь цен", "uz": "Narx kalendari", "tg": "Тақвими нарх",
                 "en": "Price calendar"},
    "kb_track": {"ru": "Мои алерты", "uz": "Alertlarim", "tg": "Огоҳиҳои ман",
                 "en": "My alerts"},
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
    "language_set": {"ru": "Готово! Язык: {name}, валюта: {cur}.",
                     "uz": "Tayyor! Til: {name}, valyuta: {cur}.",
                     "tg": "Тайёр! Забон: {name}, асъор: {cur}.",
                     "en": "Done! Language: {name}, currency: {cur}."},
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
    "start_search_first": {"ru": "Сначала найдите билеты.", "uz": "Avval chipta qidiring.",
                           "tg": "Аввал чипта ҷӯед.", "en": "Find tickets first."},
    "pax_left": {"ru": "Можно добавить ещё {n}", "uz": "Yana {n} qoʻshish mumkin",
                 "tg": "Боз {n} илова кунед", "en": "{n} more can be added"},
    "pax_total": {"ru": "{n} из 9", "uz": "{n} / 9", "tg": "{n} аз 9", "en": "{n} of 9"},
    "footnote_cache": {
        "ru": "Цены ориентировочные — актуальные на сайте бронирования.",
        "uz": "Narxlar taxminiy — aniq narx bron sahifasida.",
        "tg": "Нархҳо тахминӣ — аслӣ дар сайти брон.",
        "en": "Fares are indicative — confirm on the booking site.",
    },
    "discover_title": {"ru": "Куда сейчас дешевле", "uz": "Hozir qayer arzon",
                       "tg": "Ҳозир куҷо арзонтар", "en": "Cheap destinations right now"},
    "discover_need_from": {"ru": "Сначала укажите город вылета в поиске — тогда покажу, куда дешевле.",
                           "en": "Set a departure city in search first — then I’ll show cheap destinations."},
    "cabinet_title": {"ru": "Кабинет", "uz": "Kabinet", "tg": "Кабинет", "en": "Account"},
    "cabinet_lang": {"ru": "Язык: {name}", "uz": "Til: {name}", "tg": "Забон: {name}", "en": "Language: {name}"},
    "cabinet_cur": {"ru": "Валюта: {cur}", "uz": "Valyuta: {cur}", "tg": "Асъор: {cur}", "en": "Currency: {cur}"},
    "premium_text": {
        "ru": "Подписка\nБольше алертов, гибкие даты и приоритет в поиске.\nПока без оплаты — все функции открыты.",
        "uz": "Obuna\nKoʻproq alert, mos sanalar. Hozircha barchasi ochiq.",
        "tg": "Обуна\nОгоҳиҳои бештар. Ҳоло ҳама чиз кушода аст.",
        "en": "Premium\nMore alerts, flexible dates, search priority.\nNothing to pay yet — everything is open.",
    },
    "route_from": {"ru": "Откуда: {s}", "uz": "Qayerdan: {s}", "tg": "Аз: {s}", "en": "From: {s}"},
    "layover_in": {"ru": "пересадка {t} в {city}", "uz": "{city} da {t} transfer",
                   "tg": "истгоҳ {t} дар {city}", "en": "{t} layover in {city}"},
    "bag_yes": {"ru": "багаж", "uz": "bagaj", "tg": "бор", "en": "bags"},
    "bag_no": {"ru": "без багажа", "uz": "bagajsiz", "tg": "бе бор", "en": "no bags"},
    "direct": {"ru": "прямой", "uz": "toʻgʻri", "tg": "мустақим", "ky": "түз",
               "kk": "тікелей", "tk": "göni", "az": "birbaşa", "be": "прямы", "en": "direct"},
    "leg_back": {"ru": "обратно", "uz": "qaytish", "tg": "бозгашт", "en": "return"},
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = normalize(lang)
    entry = STRINGS.get(key, {})
    template = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    return template.format(**kwargs) if kwargs else template


def language_label(lang: str) -> str:
    return LANG_META.get(normalize(lang), lang)
