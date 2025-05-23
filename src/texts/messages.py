# All user-facing messages and button texts for Allkinds Bot

MESSAGES = {
    "en": {
        # --- Onboarding ---
        "ONBOARDING_NICKNAME_TOO_SHORT": "👋 Whoops! Nicknames need 2+ chars. Mind trying again?",
        "ONBOARDING_INTERNAL_ERROR": "😕 Hmm, something glitched. Hit /start and we'll try again.",
        "ONBOARDING_SEND_PHOTO": "📸 Mind snapping a quick pic for your profile?",
        "ONBOARDING_PHOTO_REQUIRED": "🙌 A photo helps people recognize you—go ahead and send one.",
        "ONBOARDING_SEND_LOCATION": "📍 Tap below to share your location or type City, Country so we can find folks nearby.",
        "ONBOARDING_LOCATION_REQUIRED": "⚡️ We can't match you without location—share it via button or text (e.g. Berlin, Germany).",
        "ONBOARDING_LOCATION_SAVED": "✅ Got it—your location's all set!",
        "ONBOARDING_SOMETHING_WRONG": "😕 Uh-oh, something went sideways. Try /start to begin again.",
        # --- Groups ---
        "GROUPS_NOT_IN_ANY": "👀 You haven't joined any groups yet. Want to join one?",
        "GROUPS_LEAVE_CONFIRM": "❓ Confirm leaving <b>{group_name}</b>? Your data will be removed.",
        "GROUPS_DELETE_CONFIRM": "❗️ Deleting group <b>{group_name}</b>. This is final.",
        "GROUPS_NAME_EMPTY": "🤔 Group name can't be blank. Enter it now:",
        "GROUPS_DESC_EMPTY": "📝 A quick description, please—what's this group about?",
        "GROUPS_CREATED": "🚀 '{group_name}' created! Share this code: {invite_code}",
        "GROUPS_JOIN_INVALID_CODE": "😕 That code didn't work. Enter a 5-char code:",
        "GROUPS_JOIN_NOT_FOUND": "🔍 No group matches that code. Try again?",
        "GROUPS_JOIN_ONBOARDING": "👋 Joining '{group_name}'. What nickname will you use?",
        "GROUPS_JOINED": "🌟 Welcome aboard '{group_name}'! Enjoy +{bonus}💎.",
        "GROUPS_NO_NEW_QUESTIONS": "🤷‍♂️ No new questions yet. Want to ask one?",
        "GROUPS_PROFILE_SETUP": "🔧 Time to personalise—enter your nickname:",
        "GROUPS_REVIEW_ANSWERED": "🔍 Here are your answered questions:",
        "GROUPS_FIND_MATCH": "⚡ Who Matches You Most?",
        "GROUPS_SELECT": "👉 Which group do you want to switch to?",
        "GROUPS_WELCOME_ADMIN": "👋 Hey admin! Ready to manage your crew?",
        "GROUPS_WELCOME": "👋 Welcome to Allkinds! Enter a code to join.",
        "GROUPS_SWITCH_TO": "🔄 Switch to {group_name} now.",
        "GROUPS_INVITE_LINK": "🎉 <b>{group_name}</b>\n{group_desc}\nInvite: {deeplink}\nCode: {invite_code}",
        # --- Questions ---
        "QUESTION_TOO_SHORT": "😅 Question's short—add some detail!",
        "QUESTION_MUST_JOIN_GROUP": "🔒 Join a group first to ask questions.",
        "QUESTION_DUPLICATE": "🤔 That question's already here. Try another.",
        "QUESTION_REJECTED": "🚫 This question didn't pass moderation.",
        "QUESTION_ADDED": "🎉 Question added! +{points}💎 to your account.",
        "QUESTION_DELETED": "🗑 Question deleted.",
        "QUESTION_ALREADY_DELETED": "🤷‍♂️ That question's already gone.",
        "QUESTION_ONLY_AUTHOR_OR_CREATOR": "🔒 Only you or the creator can delete this.",
        "QUESTION_ANSWER_SAVED": "✅ Your answer's saved.",
        "QUESTION_NO_ANSWERED": "🤔 No answers yet. Be the first?",
        "QUESTION_MORE_ANSWERED": "⬇️ More answered questions below:",
        "QUESTION_NO_MORE_ANSWERED": "🙌 That's all the answers for now.",
        "QUESTION_CAN_CHANGE_ANSWER": "✏️ Want to update your answer?",
        "QUESTION_INTERNAL_ERROR": "😕 Oops, unexpected error. Please try again.",
        "QUESTION_LOAD_ANSWERED": "⬇️ Load answered questions",
        "QUESTION_LOAD_MORE": "⬇️ Load more",
        "QUESTION_DELETE": "🗑 Delete",
        # --- Match ---
        "MATCH_NO_VALID": "🤔 No matches yet. Answer a few more to find them!",
        "MATCH_FOUND": "🎉 <b>{nickname}</b>\nMatch: <b>{similarity}%</b> ({common_questions} common, from {valid_users_count})",
        "MATCH_AI_CHEMISTRY": "🧬 Discover & Connect with AI",
        "MATCH_SHOW_AGAIN": "🔁 Show again",
        "MATCH_DONT_SHOW": "🚫 Don't show again",
        # --- System/General ---
        "INSTRUCTIONS_TEXT": (
            "1️⃣ Join a group  "
            "\n2️⃣ Answer questions — earn +1💎 each  "
            "\n3️⃣ Ask your own yes/no Q — get +5💎  "
            "\n4️⃣ Spend 10💎 to find your top match  "
            "\n5️⃣ Head over to Allkinds.Chat and see who really clicks ✨"
        ),
        # --- Buttons ---
        "BTN_CREATE_GROUP": "🌀 Kick off a new group",
        "BTN_JOIN_GROUP": "🔑 Join with an invite code",
        "BTN_SWITCH_TO": "🔄 Switch to {group_name}",
        "BTN_DELETE_GROUP": "🗑️ Delete {group_name}",
        "BTN_LEAVE_GROUP": "👋 Leave {group_name}",
        "BTN_DELETE": "🗑 Delete",
        "BTN_CANCEL": "❌ Cancel",
        "BTN_SEND_LOCATION": "📍 Share your location",
        "BTN_WHO_IS_VIBING": "✨ Who's vibing highest right now",
        "NO_AVAILABLE_ANSWERED_QUESTIONS": "🫥 You answered some Qs, but they were deleted—nothing to review.",
        "UNANSWERED_QUESTIONS_MSG": "🕑 You have <b>{count}</b> unanswered question(s) left.",
        "BTN_LOAD_UNANSWERED": "🔄 Load unanswered questions",
    },
    "ru": {
        # --- Onboarding ---
        "ONBOARDING_NICKNAME_TOO_SHORT": "👋 Ой! Никнейм должен быть не короче 2 символов. Попробуешь ещё раз?",
        "ONBOARDING_INTERNAL_ERROR": "😕 Хм, что-то сломалось. Напиши /start, и попробуем ещё раз.",
        "ONBOARDING_SEND_PHOTO": "📸 Скинь быстрый снимок для профиля, ок?",
        "ONBOARDING_PHOTO_REQUIRED": "🙌 Фото помогает людям узнать тебя — отправь, пожалуйста.",
        "ONBOARDING_SEND_LOCATION": "📍 Нажми ниже, чтобы поделиться локацией, или введи «Город, Страна», чтобы найти людей рядом.",
        "ONBOARDING_LOCATION_REQUIRED": "⚡️ Без локации не найдём для тебя совпадения — поделись ей кнопкой или напиши (напр. Berlin, Germany).",
        "ONBOARDING_LOCATION_SAVED": "✅ Понял — локация сохранена!",
        "ONBOARDING_SOMETHING_WRONG": "😕 Упс, что-то пошло не так. Напиши /start, чтобы начать заново.",
        # --- Groups ---
        "GROUPS_NOT_IN_ANY": "👀 Ты ещё ни в одной группе. Присоединим тебя к какой-нибудь?",
        "GROUPS_LEAVE_CONFIRM": "❓ Точно покидаем <b>{group_name}</b>? Твои данные удалятся.",
        "GROUPS_DELETE_CONFIRM": "❗️ Удаляем группу <b>{group_name}</b>. Это навсегда.",
        "GROUPS_NAME_EMPTY": "🤔 Название группы не может быть пустым. Введи его:",
        "GROUPS_DESC_EMPTY": "📝 Коротко опиши группу — о чём она?",
        "GROUPS_CREATED": "🚀 «{group_name}» создана! Поделись этим кодом: {invite_code}",
        "GROUPS_JOIN_INVALID_CODE": "😕 Этот код не сработал. Введи код из 5 символов:",
        "GROUPS_JOIN_NOT_FOUND": "🔍 Ни одна группа не нашлась по этому коду. Попробовать ещё раз?",
        "GROUPS_JOIN_ONBOARDING": "👋 Входим в «{group_name}». Какой ник возьмёшь?",
        "GROUPS_JOINED": "🌟 Добро пожаловать в «{group_name}»! Тебе +{bonus}💎.",
        "GROUPS_NO_NEW_QUESTIONS": "🤷‍♂️ Новых вопросов пока нет. Хочешь задать свой?",
        "GROUPS_PROFILE_SETUP": "🔧 Давай настроим профиль — введи свой ник:",
        "GROUPS_REVIEW_ANSWERED": "🔍 Вот твои ответы на вопросы:",
        "GROUPS_FIND_MATCH": "⚡ Кто лучше всего совпадает с тобой?",
        "GROUPS_SELECT": "👉 На какую группу хочешь переключиться?",
        "GROUPS_WELCOME_ADMIN": "👋 Привет, админ! Готов управлять своей командой?",
        "GROUPS_WELCOME": "👋 Добро пожаловать в Allkinds! Введи код, чтобы присоединиться.",
        "GROUPS_SWITCH_TO": "🔄 Сразу переключимся на «{group_name}».",
        "GROUPS_INVITE_LINK": "🎉 <b>{group_name}</b>\n{group_desc}\nПриглашение: {deeplink}\nКод: {invite_code}",
        # --- Questions ---
        "QUESTION_TOO_SHORT": "😅 Вопрос слишком короткий — добавь деталей!",
        "QUESTION_MUST_JOIN_GROUP": "🔒 Сначала присоединитесь к группе, чтобы задавать вопросы.",
        "QUESTION_DUPLICATE": "🤔 Такой вопрос уже есть. Придумай другой.",
        "QUESTION_REJECTED": "🚫 Этот вопрос не прошёл модерацию.",
        "QUESTION_ADDED": "🎉 Вопрос добавлен! Тебе +{points}💎.",
        "QUESTION_DELETED": "🗑 Вопрос удалён.",
        "QUESTION_ALREADY_DELETED": "🤷‍♂️ Этот вопрос уже удалён.",
        "QUESTION_ONLY_AUTHOR_OR_CREATOR": "🔒 Удалить может только ты или создатель группы.",
        "QUESTION_ANSWER_SAVED": "✅ Твой ответ сохранён.",
        "QUESTION_NO_ANSWERED": "🤔 Ответов пока нет. Будешь первым?",
        "QUESTION_MORE_ANSWERED": "⬇️ Ещё ответы ниже:",
        "QUESTION_NO_MORE_ANSWERED": "🙌 На данный момент это все ответы.",
        "QUESTION_CAN_CHANGE_ANSWER": "✏️ Хочешь изменить свой ответ?",
        "QUESTION_INTERNAL_ERROR": "😕 Упс, неожиданная ошибка. Попробуй ещё раз.",
        "QUESTION_LOAD_ANSWERED": "⬇️ Загрузить сохранённые ответы",
        "QUESTION_LOAD_MORE": "⬇️ Загрузить ещё",
        "QUESTION_DELETE": "🗑 Удалить",
        # --- Match ---
        "MATCH_NO_VALID": "🤔 Совпадений ещё нет. Ответь на пару вопросов, чтобы найти их!",
        "MATCH_FOUND": "🎉 <b>{nickname}</b>\nСовпадение: <b>{similarity}%</b> ({common_questions} общих вопросов, из {valid_users_count} пользователей)",
        "MATCH_AI_CHEMISTRY": "🧬 Исследуй AI-химию и общайся",
        "MATCH_SHOW_AGAIN": "🔁 Показать снова",
        "MATCH_DONT_SHOW": "🚫 Больше не показывать",
        # --- System/General ---
        "INSTRUCTIONS_TEXT": (
            "1️⃣ Присоединияйся к группе  "
            "\n2️⃣ Отвечать на вопросы — +1💎 за каждый  "
            "\n3️⃣ Задать свой вопрос да/нет — +5💎  "
            "\n4️⃣ Потратить 10💎, чтобы найти лучший матч  "
            "\n5️⃣ Перейти в Allkinds.Chat и увидеть, кто действительно подходит ✨"
        ),
        # --- Buttons ---
        "BTN_CREATE_GROUP": "🌀 Запустить новую группу",
        "BTN_JOIN_GROUP": "🔑 Присоединиться по коду приглашения",
        "BTN_SWITCH_TO": "🔄 Переключиться на «{group_name}»",
        "BTN_DELETE_GROUP": "🗑️ Удалить «{group_name}»",
        "BTN_LEAVE_GROUP": "👋 Выйти из «{group_name}»",
        "BTN_DELETE": "🗑 Удалить",
        "BTN_CANCEL": "❌ Отмена",
        "BTN_SEND_LOCATION": "📍 Поделиться своей локацией",
        "BTN_WHO_IS_VIBING": "✨ Кто сейчас на волне сильнее всех",
        "NO_AVAILABLE_ANSWERED_QUESTIONS": "🫥 Ты отвечал на вопросы, но их удалили — нечего просматривать.",
        "UNANSWERED_QUESTIONS_MSG": "🕑 У вас осталось <b>{count}</b> неотвеченных вопрос(а/ов).",
        "BTN_LOAD_UNANSWERED": "🔄 Показать неотвеченные",
    },
}

def get_message(key, user, **kwargs):
    lang = getattr(user, 'language', None)
    if lang not in MESSAGES:
        lang = 'en'
    msg = MESSAGES[lang].get(key) or MESSAGES['en'].get(key) or key
    print(f"[DEBUG get_message] lang={lang}, key={key}, msg={msg}")
    if kwargs:
        return msg.format(**kwargs)
    return msg

# --- Onboarding ---
ONBOARDING_NICKNAME_TOO_SHORT = "ONBOARDING_NICKNAME_TOO_SHORT"
ONBOARDING_INTERNAL_ERROR = "ONBOARDING_INTERNAL_ERROR"
ONBOARDING_SEND_PHOTO = "ONBOARDING_SEND_PHOTO"
ONBOARDING_PHOTO_REQUIRED = "ONBOARDING_PHOTO_REQUIRED"
ONBOARDING_SEND_LOCATION = "ONBOARDING_SEND_LOCATION"
ONBOARDING_LOCATION_REQUIRED = "ONBOARDING_LOCATION_REQUIRED"
ONBOARDING_LOCATION_SAVED = "ONBOARDING_LOCATION_SAVED"
ONBOARDING_SOMETHING_WRONG = "ONBOARDING_SOMETHING_WRONG"

# --- Groups ---
GROUPS_NOT_IN_ANY = "GROUPS_NOT_IN_ANY"
GROUPS_LEAVE_CONFIRM = "GROUPS_LEAVE_CONFIRM"
GROUPS_DELETE_CONFIRM = "GROUPS_DELETE_CONFIRM"
GROUPS_NAME_EMPTY = "GROUPS_NAME_EMPTY"
GROUPS_DESC_EMPTY = "GROUPS_DESC_EMPTY"
GROUPS_CREATED = "GROUPS_CREATED"
GROUPS_JOIN_INVALID_CODE = "GROUPS_JOIN_INVALID_CODE"
GROUPS_JOIN_NOT_FOUND = "GROUPS_JOIN_NOT_FOUND"
GROUPS_JOIN_ONBOARDING = "GROUPS_JOIN_ONBOARDING"
GROUPS_JOINED = "GROUPS_JOINED"
GROUPS_NO_NEW_QUESTIONS = "GROUPS_NO_NEW_QUESTIONS"
GROUPS_PROFILE_SETUP = "GROUPS_PROFILE_SETUP"
GROUPS_REVIEW_ANSWERED = "GROUPS_REVIEW_ANSWERED"
GROUPS_FIND_MATCH = "GROUPS_FIND_MATCH"
GROUPS_SELECT = "GROUPS_SELECT"
GROUPS_WELCOME_ADMIN = "GROUPS_WELCOME_ADMIN"
GROUPS_WELCOME = "GROUPS_WELCOME"
GROUPS_SWITCH_TO = "GROUPS_SWITCH_TO"
GROUPS_INVITE_LINK = "GROUPS_INVITE_LINK"

# --- Questions ---
QUESTION_TOO_SHORT = "QUESTION_TOO_SHORT"
QUESTION_MUST_JOIN_GROUP = "QUESTION_MUST_JOIN_GROUP"
QUESTION_DUPLICATE = "QUESTION_DUPLICATE"
QUESTION_REJECTED = "QUESTION_REJECTED"
QUESTION_ADDED = "QUESTION_ADDED"
QUESTION_DELETED = "QUESTION_DELETED"
QUESTION_ALREADY_DELETED = "QUESTION_ALREADY_DELETED"
QUESTION_ONLY_AUTHOR_OR_CREATOR = "QUESTION_ONLY_AUTHOR_OR_CREATOR"
QUESTION_ANSWER_SAVED = "QUESTION_ANSWER_SAVED"
QUESTION_NO_ANSWERED = "QUESTION_NO_ANSWERED"
QUESTION_MORE_ANSWERED = "QUESTION_MORE_ANSWERED"
QUESTION_NO_MORE_ANSWERED = "QUESTION_NO_MORE_ANSWERED"
QUESTION_CAN_CHANGE_ANSWER = "QUESTION_CAN_CHANGE_ANSWER"
QUESTION_INTERNAL_ERROR = "QUESTION_INTERNAL_ERROR"
QUESTION_LOAD_ANSWERED = "QUESTION_LOAD_ANSWERED"
QUESTION_LOAD_MORE = "QUESTION_LOAD_MORE"
QUESTION_DELETE = "QUESTION_DELETE"

# --- Match ---
MATCH_NO_VALID = "MATCH_NO_VALID"
MATCH_FOUND = "MATCH_FOUND"
MATCH_AI_CHEMISTRY = "MATCH_AI_CHEMISTRY"
MATCH_SHOW_AGAIN = "MATCH_SHOW_AGAIN"
MATCH_DONT_SHOW = "MATCH_DONT_SHOW"

# --- System/General ---
INSTRUCTIONS_TEXT = "INSTRUCTIONS_TEXT"

# --- Buttons ---
BTN_CREATE_GROUP = "BTN_CREATE_GROUP"
BTN_JOIN_GROUP = "BTN_JOIN_GROUP"
BTN_SWITCH_TO = "BTN_SWITCH_TO"
BTN_DELETE_GROUP = "BTN_DELETE_GROUP"
BTN_LEAVE_GROUP = "BTN_LEAVE_GROUP"
BTN_DELETE = "BTN_DELETE"
BTN_CANCEL = "BTN_CANCEL"
BTN_SEND_LOCATION = "BTN_SEND_LOCATION"
BTN_WHO_IS_VIBING = "BTN_WHO_IS_VIBING"

NO_AVAILABLE_ANSWERED_QUESTIONS = "NO_AVAILABLE_ANSWERED_QUESTIONS"

UNANSWERED_QUESTIONS_MSG = "UNANSWERED_QUESTIONS_MSG"
BTN_LOAD_UNANSWERED = "BTN_LOAD_UNANSWERED" 