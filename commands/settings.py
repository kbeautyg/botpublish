from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from zoneinfo import ZoneInfo
from storage import supabase_db
from commands import TEXTS

router = Router()

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=2)
    lang = "ru"
    user = supabase_db.db.get_user(user_id)
    if user:
        lang = user.get("language", "ru")

    # Если просто /settings — показать настройки + инструкцию
    if len(args) == 1:
        if not user:
            user = supabase_db.db.ensure_user(user_id)
            lang = user.get("language", lang)
        tz = user.get("timezone", "UTC")
        lang_name = TEXTS[lang]['lang_ru'] if user.get("language") == "ru" else TEXTS[lang]['lang_en']
        date_fmt = user.get("date_format", "YYYY-MM-DD")
        time_fmt = user.get("time_format", "HH:MM")
        notify_val = user.get("notify_before", 0)
        notify_str = (str(notify_val) + (" мин." if lang == "ru" else " min")) if notify_val else ("выкл." if lang == "ru" else "off")

        msg = (
            f"Ваши настройки:\n"
            f"Часовой пояс: {tz}\n"
            f"Язык: {lang_name}\n"
            f"Формат даты: {date_fmt}\n"
            f"Формат времени: {time_fmt}\n"
            f"Уведомления: {notify_str}\n\n"
            "Для изменения настроек используйте команды:\n"
            "/settings tz Europe/Moscow — установить часовой пояс\n"
            "/settings lang ru — язык интерфейса (ru, en)\n"
            "/settings datefmt YYYY-MM-DD — формат даты (например: YYYY-MM-DD)\n"
            "/settings timefmt HH:MM — формат времени (например: HH:MM)\n"
            "/settings notify 10 — напоминание за N минут до публикации (0 — выкл.)\n"
            "\nПримеры:\n"
            "/settings tz Europe/Moscow\n"
            "/settings lang en\n"
            "/settings datefmt DD.MM.YYYY\n"
            "/settings timefmt HH:mm\n"
            "/settings notify 15\n"
        )
        await message.answer(msg)
        return

    # иначе разбираем, что меняем
    sub = args[1].lower()
    if sub in ("tz", "timezone", "часовой", "часовой_пояс"):
        if len(args) < 3:
            await message.answer("Пример: /settings tz Europe/Moscow")
            return
        tz_input = args[2]
        try:
            ZoneInfo(tz_input)
        except Exception:
            await message.answer("Ошибка: неверный идентификатор часового пояса. Пример: Europe/Moscow или UTC")
            return
        supabase_db.db.update_user(user_id, {"timezone": tz_input})
        await message.answer(f"Часовой пояс обновлен: {tz_input}")
    elif sub in ("lang", "language", "язык"):
        if len(args) < 3:
            await message.answer("Пример: /settings lang ru")
            return
        val = args[2].lower()
        if val in ("ru", "русский", "rus"):
            new_lang = "ru"
        elif val in ("en", "eng", "english", "английский"):
            new_lang = "en"
        else:
            await message.answer("Ошибка: язык должен быть ru или en")
            return
        supabase_db.db.update_user(user_id, {"language": new_lang})
        lang_name = "Русский" if new_lang == "ru" else "English"
        await message.answer(f"Язык интерфейса обновлен: {lang_name}")
    elif sub in ("datefmt", "date_format", "формат_даты"):
        if len(args) < 3:
            await message.answer("Пример: /settings datefmt YYYY-MM-DD")
            return
        fmt = args[2].upper()
        if not ("Y" in fmt and "M" in fmt and "D" in fmt):
            await message.answer("Ошибка: неверный формат даты. Пример: YYYY-MM-DD")
            return
        supabase_db.db.update_user(user_id, {"date_format": fmt})
        await message.answer(f"Формат даты обновлен: {fmt}")
    elif sub in ("timefmt", "time_format", "формат_времени"):
        if len(args) < 3:
            await message.answer("Пример: /settings timefmt HH:MM")
            return
        fmt = args[2]
        if "H" not in fmt.upper() or "M" not in fmt.upper():
            await message.answer("Ошибка: неверный формат времени. Пример: HH:MM")
            return
        supabase_db.db.update_user(user_id, {"time_format": fmt})
        await message.answer(f"Формат времени обновлен: {fmt}")
    elif sub in ("notify", "notifications", "уведомления"):
        if len(args) < 3:
            await message.answer("Пример: /settings notify 10")
            return
        val = args[2].lower()
        if val in ("0", "off", "нет", "none"):
            minutes = 0
        else:
            try:
                minutes = int(val)
            except:
                minutes = None
        if minutes is None or minutes < 0:
            await message.answer("Ошибка: укажите количество минут (например: 10), либо 0 чтобы отключить")
            return
        supabase_db.db.update_user(user_id, {"notify_before": minutes})
        msg = "Уведомления выключены" if minutes == 0 else f"Напоминание: за {minutes} минут до публикации"
        await message.answer(msg)
    else:
        await message.answer("Неизвестная настройка. Используйте только tz, lang, datefmt, timefmt, notify")
