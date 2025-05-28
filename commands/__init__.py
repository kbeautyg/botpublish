# commands/__init__.py
"""
Command handlers package (multi-language support via TEXTS).
"""
TEXTS = {
    'ru': {
        'start_welcome': "Привет! Я бот для отложенного постинга.\nИспользуйте /help для списка команд.",
        'help': ("Команды:\n"
                 "/create – создать пост\n"
                 "/list – список отложенных постов\n"
                 "/edit <ID> – редактировать пост\n"
                 "/delete <ID> – удалить пост\n"
                 "/channels – управление каналами\n"
                 "/settings – настройки пользователя\n"
                 "/cancel – отменить ввод"),
        'channels_no_channels': "Список каналов пуст. Добавьте канал:\n/channels add <ID_канала или @username>",
        'channels_list_title': "Подключенные каналы:",
        'channels_item': "- {name} (ID: {id})",
        'channels_add_usage': "Использование:\n/channels add <ID_канала или @username>",
        'channels_remove_usage': "Использование:\n/channels remove <ID_канала>",
        'channels_added': "Канал «{name}» добавлен.",
        'channels_add_error': "Не удалось получить канал: {error}",
        'channels_removed': "Канал удалён.",
        'channels_not_found': "Канал не найден.",
        'channels_unknown_command': "Неизвестная подкоманда. Используйте /channels add | remove",
        'no_channels': "Нет доступных каналов. Сначала добавьте канал через /channels.",
        'create_step1': "Шаг 1/8: отправьте текст поста (или /skip).",
        'create_step2': "Шаг 2/8: пришлите фото или видео, или /skip.",
        'create_step2_retry': "Отправьте фото или видео, или /skip.",
        'create_step3': "Шаг 3/8: выберите формат (Markdown, HTML или Без форматирования).",
        'create_step4': ("Шаг 4/8: отправьте кнопки.\n"
                         "Каждая кнопка на новой строке: «Текст | URL».\n"
                         "Если кнопки не нужны – отправьте /skip."),
        'create_step5': "Шаг 5/8: отправьте дату и время публикации в формате {format}.",
        'create_time_error': "Неверный формат. Пример: {example}.",
        'create_step6': ("Шаг 6/8: интервал повторения поста.\n"
                         "Напр.: 1d (ежедневно), 7d (еженедельно), 12h (каждые 12 часов), 0 или /skip – без повтора."),
        'create_repeat_error': "Неверный формат интервала. Примеры: 0, 1d, 12h, 30m.",
        'create_step7': "Шаг 7/8: выберите канал для публикации (введите номер).",
        'create_channel_error': "Канал не найден. Введите номер или ID.",
        'confirm_post_scheduled': "Пост запланирован ✅",
        'confirm_post_draft': "Черновик сохранён ✅",
        'confirm_post_cancel': "Отменено.",
        'edit_usage': "Использование: /edit <ID поста>",
        'edit_invalid_id': "Некорректный ID поста.",
        'edit_post_not_found': "Пост с таким ID не найден.",
        'edit_post_published': "Этот пост уже опубликован, редактирование невозможно.",
        'edit_begin': "Редактирование поста #{id}.\nТекущий текст: \"{text}\"\nОтправьте новый текст или /skip, чтобы оставить без изменений.",
        'edit_current_media': "Текущее медиа: {info} прикреплено.\nОтправьте новое фото или видео, чтобы заменить, или /skip, чтобы оставить, или введите 'нет' для удаления медиа.",
        'edit_no_media': "Для поста нет медиа.\nОтправьте фото или видео, чтобы добавить, или /skip, чтобы пропустить.",
        'edit_current_format': "Текущий формат: {format}. Выберите новый формат или отправьте /skip для сохранения текущего.",
        'edit_current_buttons': "Текущие кнопки:\n{buttons_list}\nОтправьте новые кнопки (Текст | URL), или /skip для сохранения, или 'нет' для удаления всех.",
        'edit_no_buttons': "Для поста нет кнопок.\nОтправьте кнопки в формате Текст | URL, или /skip, чтобы пропустить, или 'нет' чтобы оставить без кнопок.",
        'edit_current_time': "Текущее время публикации: {time}\nВведите новую дату/время в формате {format}, или /skip для сохранения, или 'none' для удаления времени (черновик).",
        'edit_time_error': "Неверный формат. Введите в формате {format} или /skip.",
        'edit_current_repeat': "Текущий интервал повтора: {repeat}\nВведите новый интервал (0 – без повтора) или /skip для сохранения.",
        'edit_repeat_error': "Неверный формат интервала. Примеры: 0, 1d, 12h, 30m.",
        'edit_choose_channel': "Выберите новый канал для поста (или нажмите 'Оставить текущий'):",
        'edit_keep_current_channel': "Оставить текущий",
        'confirm_changes_saved': "Изменения сохранены для поста #{id}.",
        'edit_cancelled': "Редактирование поста отменено.",
        'edit_saved_notify': "Пост отредактирован ✅",
        'edit_cancel_notify': "Редактирование отменено ❌",
        'no_posts': "Нет запланированных постов.",
        'scheduled_posts_title': "Запланированные посты:",
        'delete_usage': "Использование: /delete <ID поста>",
        'delete_invalid_id': "Некорректный ID поста.",
        'delete_not_found': "Пост с таким ID не найден.",
        'delete_already_published': "Этот пост уже был опубликован, его нельзя удалить.",
        'delete_success': "Пост #{id} удалён.",
        'no_text': "(без текста)",
        'media_photo': "фото",
        'media_video': "видео",
        'media_media': "медиа",
        'settings_current': ("Ваши настройки:\n"
                             "Часовой пояс: {tz}\n"
                             "Язык: {lang}\n"
                             "Формат даты: {date_fmt}\n"
                             "Формат времени: {time_fmt}\n"
                             "Уведомления: {notify}"),
        'settings_timezone_usage': "Использование:\n/settings tz <часовой пояс>",
        'settings_language_usage': "Использование:\n/settings lang <ru|en>",
        'settings_datefmt_usage': "Использование:\n/settings datefmt <формат даты> (например, DD.MM.YYYY)",
        'settings_timefmt_usage': "Использование:\n/settings timefmt <формат времени> (например, HH:MM)",
        'settings_notify_usage': "Использование:\n/settings notify <минут до уведомления> (0 для выкл.)",
        'settings_unknown': "Неизвестный параметр. Доступно: tz, lang, datefmt, timefmt, notify",
        'settings_tz_set': "Часовой пояс обновлён: {tz}",
        'settings_lang_set': "Язык обновлён: {lang_name}",
        'settings_datefmt_set': "Формат даты обновлён: {fmt}",
        'settings_timefmt_set': "Формат времени обновлён: {fmt}",
        'settings_notify_set': "Уведомления перед публикацией: {minutes_str}",
        'settings_invalid_tz': "Неправильный часовой пояс. Пример: Europe/Moscow или UTC+3",
        'settings_invalid_lang': "Неподдерживаемый язык. Доступно: ru, en",
        'settings_invalid_datefmt': "Неверный формат даты.",
        'settings_invalid_timefmt': "Неверный формат времени.",
        'settings_invalid_notify': "Неверное значение (в минутах).",
        'lang_ru': "Русский",
        'lang_en': "Английский",
        'notify_message': "⌛️ Скоро будет опубликован пост #{id} в канале {channel} (через {minutes} мин.).",
        'notify_message_less_min': "⌛️ Скоро будет опубликован пост #{id} в канале {channel} (менее чем через минуту).",
        'error_post_failed': "⚠️ Не удалось отправить пост #{id} в канал {channel}: {error}"
    },
    'en': {
        'start_welcome': "Hello! I'm a bot for scheduling posts.\nUse /help to see available commands.",
        'help': ("Commands:\n"
                 "/create – create a post\n"
                 "/list – list scheduled posts\n"
                 "/edit <ID> – edit a post\n"
                 "/delete <ID> – delete a post\n"
                 "/channels – manage channels\n"
                 "/settings – user settings\n"
                 "/cancel – cancel input"),
        'channels_no_channels': "No channels added. Add a channel via:\n/channels add <channel_id or @username>",
        'channels_list_title': "Connected channels:",
        'channels_item': "- {name} (ID: {id})",
        'channels_add_usage': "Usage:\n/channels add <channel_id or @username>",
        'channels_remove_usage': "Usage:\n/channels remove <channel_id>",
        'channels_added': "Channel \"{name}\" added.",
        'channels_add_error': "Failed to get channel: {error}",
        'channels_removed': "Channel removed.",
        'channels_not_found': "Channel not found.",
        'channels_unknown_command': "Unknown subcommand. Use /channels add | remove",
        'no_channels': "No channels available. Please add a channel via /channels first.",
        'create_step1': "Step 1/8: send the post text (or /skip).",
        'create_step2': "Step 2/8: send a photo or video, or /skip.",
        'create_step2_retry': "Please send a photo or video, or /skip.",
        'create_step3': "Step 3/8: choose format (Markdown, HTML or None).",
        'create_step4': ("Step 4/8: send buttons.\n"
                         "One button per line in format: Text | URL.\n"
                         "If no buttons needed, send /skip."),
        'create_step5': "Step 5/8: send the date/time in format {format}.",
        'create_time_error': "Invalid format. Example: {example}.",
        'create_step6': ("Step 6/8: set repeat interval.\n"
                         "E.g. 1d (daily), 7d (weekly), 12h (every 12 hours), 0 or /skip for no repeat."),
        'create_repeat_error': "Invalid interval format. Examples: 0, 1d, 12h, 30m.",
        'create_step7': "Step 7/8: choose a channel for posting (enter number).",
        'create_channel_error': "Channel not found. Enter a number or ID.",
        'confirm_post_scheduled': "Post scheduled ✅",
        'confirm_post_draft': "Draft saved ✅",
        'confirm_post_cancel': "Cancelled.",
        'edit_usage': "Usage: /edit <post ID>",
        'edit_invalid_id': "Invalid post ID.",
        'edit_post_not_found': "Post not found.",
        'edit_post_published': "This post has already been published and cannot be edited.",
        'edit_begin': "Editing post #{id}.\nCurrent text: \"{text}\"\nSend new text or /skip to leave unchanged.",
        'edit_current_media': "Current media: {info} attached.\nSend a new photo or video to replace, or /skip to keep, or type 'none' to remove.",
        'edit_no_media': "This post has no media.\nSend a photo or video to add, or /skip to continue.",
        'edit_current_format': "Current format: {format}. Choose a new format or send /skip to keep current.",
        'edit_current_buttons': "Current buttons:\n{buttons_list}\nSend new buttons (Text | URL), or /skip to keep, or 'none' to remove all.",
        'edit_no_buttons': "This post has no buttons.\nSend buttons in Text | URL format to add, or /skip to skip, or 'none' to keep none.",
        'edit_current_time': "Current scheduled time: {time}\nEnter a new date/time in format {format}, or /skip to keep, or 'none' to unschedule (draft).",
        'edit_time_error': "Invalid format. Use {format} or /skip.",
        'edit_current_repeat': "Current repeat interval: {repeat}\nEnter a new interval (0 for none) or /skip to keep.",
        'edit_repeat_error': "Invalid interval format. Examples: 0, 1d, 12h, 30m.",
        'edit_choose_channel': "Choose a new channel for the post (or press 'Keep current'):",
        'edit_keep_current_channel': "Keep current",
        'confirm_changes_saved': "Changes saved for post #{id}.",
        'edit_cancelled': "Post editing cancelled.",
        'edit_saved_notify': "Post edited ✅",
        'edit_cancel_notify': "Edit cancelled ❌",
        'no_posts': "No scheduled posts.",
        'scheduled_posts_title': "Scheduled posts:",
        'delete_usage': "Usage: /delete <post ID>",
        'delete_invalid_id': "Invalid post ID.",
        'delete_not_found': "Post not found.",
        'delete_already_published': "This post has already been published and cannot be deleted.",
        'delete_success': "Post #{id} deleted.",
        'no_text': "(no text)",
        'media_photo': "photo",
        'media_video': "video",
        'media_media': "media",
        'settings_current': ("Your settings:\n"
                             "Timezone: {tz}\n"
                             "Language: {lang}\n"
                             "Date format: {date_fmt}\n"
                             "Time format: {time_fmt}\n"
                             "Notifications: {notify}"),
        'settings_timezone_usage': "Usage:\n/settings tz <timezone>",
        'settings_language_usage': "Usage:\n/settings lang <ru|en>",
        'settings_datefmt_usage': "Usage:\n/settings datefmt <date format> (e.g. DD.MM.YYYY)",
        'settings_timefmt_usage': "Usage:\n/settings timefmt <time format> (e.g. HH:MM)",
        'settings_notify_usage': "Usage:\n/settings notify <minutes before> (0 to disable)",
        'settings_unknown': "Unknown setting. Available: tz, lang, datefmt, timefmt, notify",
        'settings_tz_set': "Timezone updated to {tz}",
        'settings_lang_set': "Language updated to {lang_name}",
        'settings_datefmt_set': "Date format updated to {fmt}",
        'settings_timefmt_set': "Time format updated to {fmt}",
        'settings_notify_set': "Notification lead time set to {minutes_str}",
        'settings_invalid_tz': "Invalid timezone. Example: Europe/Moscow or UTC+3",
        'settings_invalid_lang': "Unsupported language. Available: ru, en",
        'settings_invalid_datefmt': "Invalid date format.",
        'settings_invalid_timefmt': "Invalid time format.",
        'settings_invalid_notify': "Invalid notification value.",
        'lang_ru': "Russian",
        'lang_en': "English",
        'notify_message': "⌛️ Post #{id} in channel {channel} will be posted in {minutes} min.",
        'notify_message_less_min': "⌛️ Post #{id} in channel {channel} will be posted in less than a minute.",
        'error_post_failed': "⚠️ Failed to send post #{id} to channel {channel}: {error}"
    }
}
