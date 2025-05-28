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
        await message.answer(TEXTS[lang]['settings_current'].format(tz=tz, lang=lang_name, date_fmt=date_fmt, time_fmt=time_fmt, notify=notify_str))
        return
    sub = args[1].lower()
    if sub in ("tz", "timezone", "часовой", "часовой_пояс"):
        if len(args) < 3:
            await message.answer(TEXTS[lang]['settings_timezone_usage'])
            return
        tz_input = args[2]
        if tz_input.upper().startswith("UTC"):
            tz_name = tz_input.upper()
            try:
                offset_hours = int(tz_name[3:].strip("+"))
            except Exception:
                await message.answer(TEXTS[lang]['settings_invalid_tz'])
                return
            offset = offset_hours
            tz_zone = f"Etc/GMT{'-' if offset >= 0 else '+'}{abs(offset)}"
            try:
                ZoneInfo(tz_zone)
            except:
                await message.answer(TEXTS[lang]['settings_invalid_tz'])
                return
            display_tz = f"UTC+{offset}" if offset >= 0 else f"UTC{offset}"
            supabase_db.db.update_user(user_id, {"timezone": tz_zone})
            await message.answer(TEXTS[lang]['settings_tz_set'].format(tz=display_tz))
        else:
            try:
                ZoneInfo(tz_input)
            except Exception:
                await message.answer(TEXTS[lang]['settings_invalid_tz'])
                return
            supabase_db.db.update_user(user_id, {"timezone": tz_input})
            await message.answer(TEXTS[lang]['settings_tz_set'].format(tz=tz_input))
    elif sub in ("lang", "language", "язык"):
        if len(args) < 3:
            await message.answer(TEXTS[lang]['settings_language_usage'])
            return
        val = args[2].lower()
        new_lang = None
        if val in ("ru", "русский", "rus"):
            new_lang = "ru"
        elif val in ("en", "eng", "english", "английский"):
            new_lang = "en"
        else:
            await message.answer(TEXTS[lang]['settings_invalid_lang'])
            return
        supabase_db.db.update_user(user_id, {"language": new_lang})
        lang = new_lang
        lang_name = TEXTS[lang]['lang_ru'] if new_lang == "ru" else TEXTS[lang]['lang_en']
        await message.answer(TEXTS[lang]['settings_lang_set'].format(lang_name=lang_name))
    elif sub in ("datefmt", "date_format", "формат_даты"):
        if len(args) < 3:
            await message.answer(TEXTS[lang]['settings_datefmt_usage'])
            return
        fmt = args[2]
        fmt_up = fmt.upper()
        if "Y" not in fmt_up or "M" not in fmt_up or "D" not in fmt_up:
            await message.answer(TEXTS[lang]['settings_invalid_datefmt'])
            return
        supabase_db.db.update_user(user_id, {"date_format": fmt_up})
        await message.answer(TEXTS[lang]['settings_datefmt_set'].format(fmt=fmt_up))
    elif sub in ("timefmt", "time_format", "формат_времени"):
        if len(args) < 3:
            await message.answer(TEXTS[lang]['settings_timefmt_usage'])
            return
        fmt = args[2]
        val_low = fmt.strip().lower()
        if val_low in ("12h", "12hr", "12-hour", "12hours"):
            fmt_up = "hh:MM AM"
        elif val_low in ("24h", "24hr", "24-hour", "24hours"):
            fmt_up = "HH:MM"
        else:
            fmt_up = fmt.upper()
        if "H" not in fmt_up or "M" not in fmt_up:
            await message.answer(TEXTS[lang]['settings_invalid_timefmt'])
            return
        supabase_db.db.update_user(user_id, {"time_format": fmt_up})
        await message.answer(TEXTS[lang]['settings_timefmt_set'].format(fmt=fmt_up))
    elif sub in ("notify", "notifications", "уведомления"):
        if len(args) < 3:
            await message.answer(TEXTS[lang]['settings_notify_usage'])
            return
        val = args[2].lower()
        if val in ("0", "off", "no", "нет", "none"):
            minutes = 0
        else:
            try:
                minutes = int(val)
            except:
                minutes = None
        if minutes is None or minutes < 0:
            await message.answer(TEXTS[lang]['settings_invalid_notify'])
            return
        supabase_db.db.update_user(user_id, {"notify_before": minutes})
        if minutes == 0:
            minutes_str = "выкл." if lang == "ru" else "off"
        else:
            minutes_str = str(minutes) + (" мин." if lang == "ru" else " min")
        await message.answer(TEXTS[lang]['settings_notify_set'].format(minutes_str=minutes_str))
    else:
        await message.answer(TEXTS[lang]['settings_unknown'])
