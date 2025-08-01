# All user-facing messages and button texts for Allkinds Bot

MESSAGES = {
    "en": {
        # --- Onboarding ---
        "ONBOARDING_NICKNAME_TOO_SHORT": "👋 Whoops! Nicknames need 2+ chars. Mind trying again?",
        "ONBOARDING_INTERNAL_ERROR": "😕 Hmm, something glitched. Hit /start and we'll try again.",
        "ONBOARDING_SEND_PHOTO": "📸 Mind adding any pic for your profile?",
        "ONBOARDING_PHOTO_REQUIRED": "🙌 A photo helps people recognize you—go ahead and send one.",
        "ONBOARDING_SEND_INTRO": "✍️ Add a short intro about yourself (optional - you can skip by typing 'skip'):",
        "ONBOARDING_INTRO_TOO_LONG": "📝 Keep it short and sweet! Max 200 characters please.",
        "ONBOARDING_SELECT_GENDER": "👤 Specify your gender:",
        "ONBOARDING_SELECT_LOOKING_FOR": "💕 Who are you looking for?",
        "ONBOARDING_SEND_LOCATION": "📍 Tap below to share your location or type City, Country so we can find folks nearby.",
        "ONBOARDING_LOCATION_REQUIRED": "⚡️ We can't match you without location—share it via button or text (e.g. Berlin, Germany).",
        "ONBOARDING_LOCATION_SAVED": "✅ Got it—your location's all set!",
        "ONBOARDING_COMPLETE": "✅ You are all set!\nEnjoy your +{bonus}💎 bonus.\nGood luck in finding good connections.",
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
        "GROUPS_JOIN_ONBOARDING": "What nickname will you use?",
        "GROUPS_JOINED": "🌟 Welcome aboard '{group_name}'!\n{group_desc}",
        "GROUPS_NO_NEW_QUESTIONS": "🤷‍♂️ No new questions yet. Want to ask one?",
        "GROUPS_PROFILE_SETUP": "🔧 Time to personalise—enter your nickname:",
        "GROUPS_REVIEW_ANSWERED": "🔍 Load your answered questions if you want to change them:",
        "GROUPS_FIND_MATCH": "👋 Welcome to <b>{group_name}</b>!\nYour balance: {balance}💎",
        "GROUPS_SELECT": "👉 Which group do you want to go to?",
        "GROUPS_WELCOME_ADMIN": "👋 Hey admin! Ready to manage your crew?",
        "GROUPS_WELCOME": "👋 Welcome to Allkinds! Enter a code to join.",
        "GROUPS_SWITCH_TO": "👉 Go to {group_name} now.",
        "GROUPS_INVITE_LINK": "🎉 <b>{group_name}</b>\n{group_desc}\nInvite: {deeplink}\nCode: {invite_code}",
        "NEW_QUESTION_NOTIFICATION": "📩 New question in queue: {question_text}...",
        "QUEUE_LOAD_UNANSWERED": "📋 Ready to answer questions from the queue?",
        "GROUPS_LEFT_SUCCESS": "👋 You have successfully left the group.",
        "GROUPS_LEFT_ERROR": "😕 Error leaving group. Please try again.",
        "GROUPS_DELETED_SUCCESS": "🗑️ Group successfully deleted.",
        "GROUPS_DELETED_ERROR": "😕 Error deleting group. Please try again.",
        # --- Questions ---
        "QUESTION_TOO_SHORT": "😅 Question's short—add some detail!",
        "QUESTION_MUST_JOIN_GROUP": "🔒 Join a group first to ask questions.",
        "QUESTION_DUPLICATE": "🤔 That question's already here. Try another.",
        "QUESTION_REJECTED": "🚫 This question didn't pass moderation.",
        "QUESTION_ADDED": "🎉 Question added! +{points}💎 to your account.",
        "QUESTION_PENDING_APPROVAL": "⏳ Your question is being reviewed by the admin.",
        "QUESTION_ADMIN_APPROVAL": "📝 New question from {author_name}:\n\n{question_text}\n\nApprove or reject?",
        "QUESTION_APPROVED_ADMIN": "✅ Question approved and sent to group members.",
        "QUESTION_REJECTED_ADMIN": "❌ Question rejected.",
        "QUESTION_APPROVED_AUTHOR": "✅ Your question was approved! +{points}💎 to your account.",
        "QUESTION_REJECTED_AUTHOR": "❌ Your question was rejected by the admin.",
        "USER_BANNED_ADMIN": "🚫 User {banned_nickname} has been banned and removed from the group.",
        "USER_BANNED_NOTIFICATION": "🚫 You have been banned from group '{group_name}' for spam behavior.",
        "USER_BANNED_JOIN_ATTEMPT": "🚫 You are banned from this group and cannot join.",
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
        "MATCH_FOUND": "🎉 {nickname}, {similarity}% ({common_questions} questions), {distance_info}\n{intro}",
        "MATCH_AI_CHEMISTRY": "💬 Start a private chat",
        "MATCH_SHOW_AGAIN": "🔁 Show again later",
        "MATCH_DONT_SHOW": "🚫 Don't show again",
        "MATCH_PREV": "<<",
        "MATCH_NEXT": ">>",
        "MATCH_NOT_ENOUGH_POINTS": "❌ Not enough points to view next match",
        "MATCH_NO_OTHERS": "There are no other participants in the group for matching yet.",
        # --- Match Connection Messages ---
        "MATCH_REQUEST_SENT": "🔔 We've notified {nickname} about your interest. We'll let you know when they make a decision!",
        "MATCH_INCOMING_REQUEST": "🤝 {nickname} wants to connect with you",
        "MATCH_REQUEST_ACCEPTED": "✅ {nickname} accepted your match request!",
        "MATCH_REQUEST_REJECTED": "😔 {nickname} declined your match request.",
        "MATCH_REQUEST_BLOCKED": "🚫 {nickname} decided not to communicate with you 😞",
        # --- System/General ---
        "INSTRUCTIONS_TEXT": (
            "🎯 How Allkinds works:\n\n"
            "❓ Ask questions that matter to you (+10💎)\n"
            "Just type your yes/no question and send it\n\n"
            "✅ Answer questions from others (+1💎)\n"
            "Every answer helps you find better matches\n\n"
            "🔍 Find your best match (-5💎)\n"
            "Use \"Who's vibing\" to see who matches you most\n\n"
            "🤝 Connect with people you like\n"
            "Send connection requests and exchange contacts\n\n"
            "💎 Earn points by participating, spend them on matches"
        ),
        # --- Buttons ---
        "BTN_CREATE_GROUP": "🌀 Kick off a new group",
        "BTN_JOIN_GROUP": "🔑 Join with an invite code",
        "BTN_SWITCH_TO": "👉 Go to {group_name}",
        "BTN_DELETE_GROUP": "🗑️ Delete {group_name}",
        "BTN_LEAVE_GROUP": "👋 Leave {group_name}",
        "BTN_DELETE": "🗑 Delete",
        "BTN_CANCEL": "❌ Cancel",
        "BTN_SEND_LOCATION": "📍 Share your location",
        "BTN_GENDER_MALE": "👨 Male",
        "BTN_GENDER_FEMALE": "👩 Female",
        "BTN_LOOKING_FOR_MALE": "👨 Male",
        "BTN_LOOKING_FOR_FEMALE": "👩 Female",
        "BTN_LOOKING_FOR_ALL": "👥 All",
        "BTN_WHO_IS_VIBING": "🔍 Who's vibing highest right now",
        "BTN_CONNECT": "🤝 Connect",
        "BTN_ACCEPT_MATCH": "✅ Accept",
        "BTN_REJECT_MATCH": "❌ Decline",
        "BTN_DECLINE_MATCH": "❌ Decline",
        "BTN_BLOCK_MATCH": "🚫 Block",
        "BTN_GO_TO_CHAT": "💬 Go to Chat",
        "BTN_GOT_IT": "✅ Got it",
        "NO_AVAILABLE_ANSWERED_QUESTIONS": "🫥 You answered some Qs, but they were deleted—nothing to review.",
        "UNANSWERED_QUESTIONS_MSG": "🕑 You have <b>{count}</b> unanswered question(s) left.",
        "BTN_LOAD_UNANSWERED": "🔄 Load unanswered questions",
        "TOKEN_EXPIRE_REMINDER": "⏳ Your token is about to expire. Click the button to extend your account.",
        "TOKEN_EXTEND": "🔄 Extend",
        "TOKEN_EXTENDED": "✅ Your token has been extended.",
        "QUESTIONS_ALL_ANSWERED": "🎉 That's all the questions for now, come back later!",
    },
    "ru": {
        # --- Onboarding ---
        "ONBOARDING_NICKNAME_TOO_SHORT": "👋 Упс! Никнейм должен быть от 2+ символов. Попробуешь ещё раз?",
        "ONBOARDING_INTERNAL_ERROR": "😕 Хм, что-то глючит. Нажми /start и попробуем снова.",
        "ONBOARDING_SEND_PHOTO": "📸 Добавь любое фото/картинку в профиль?",
        "ONBOARDING_PHOTO_REQUIRED": "🙌 Фото помогает людям узнать тебя — отправь одно.",
        "ONBOARDING_SEND_INTRO": "✍️ Добавь короткое интро о себе (необязательно - можешь пропустить, написав 'пропустить'):",
        "ONBOARDING_INTRO_TOO_LONG": "📝 Давай покороче! Максимум 200 символов пожалуйста.",
        "ONBOARDING_SELECT_GENDER": "👤 Укажите ваш пол:",
        "ONBOARDING_SELECT_LOOKING_FOR": "💕 Кого вы ищете?",
        "ONBOARDING_SEND_LOCATION": "📍 Нажми ниже, чтобы поделиться локацией, или введи Город, Страна, чтобы мы нашли людей поблизости.",
        "ONBOARDING_LOCATION_REQUIRED": "⚡️ Мы не сможем найти тебе пару без локации — поделись через кнопку или текстом (например, Berlin, Germany).",
        "ONBOARDING_LOCATION_SAVED": "✅ Отлично — твоя локация настроена!",
        "ONBOARDING_COMPLETE": "✅ Ты готов к работе!\nПолучай свой +{bonus}💎 бонус.\nУдачи в поиске хороших связей.",
        "ONBOARDING_SOMETHING_WRONG": "😕 Хм, что-то пошло не так. Попробуй /start, чтобы начать заново.",
        # --- Groups ---
        "GROUPS_NOT_IN_ANY": "👀 Ты ещё не присоединился ни к одной группе. Хочешь присоединиться?",
        "GROUPS_LEAVE_CONFIRM": "❓ Подтвердить выход из <b>{group_name}</b>? Твои данные будут удалены.",
        "GROUPS_DELETE_CONFIRM": "❗️ Удаление группы <b>{group_name}</b>. Это окончательно.",
        "GROUPS_NAME_EMPTY": "🤔 Название группы не может быть пустым. Введи его сейчас:",
        "GROUPS_DESC_EMPTY": "📝 Добавь краткое описание — о чём эта группа?",
        "GROUPS_CREATED": "🚀 '{group_name}' создана! Поделись этим кодом: {invite_code}",
        "GROUPS_JOIN_INVALID_CODE": "😕 Этот код не сработал. Введи 5-символьный код:",
        "GROUPS_JOIN_NOT_FOUND": "🔍 Ни одна группа не соответствует этому коду. Попробовать снова?",
        "GROUPS_JOIN_ONBOARDING": "Какой никнейм будешь использовать?",
        "GROUPS_JOINED": "🌟 Добро пожаловать на борт '{group_name}'!\n{group_desc}",
        "GROUPS_NO_NEW_QUESTIONS": "🤷‍♂️ Новых вопросов пока нет. Хочешь задать один?",
        "GROUPS_PROFILE_SETUP": "🔧 Введи какой-нибудь никнейм:",
        "GROUPS_REVIEW_ANSWERED": "🔍 Загрузи свои отвеченные вопросы, если хочешь изменить ответы:",
        "GROUPS_FIND_MATCH": "👋 Добро пожаловать в <b>{group_name}</b>!\nТвой баланс: {balance}💎",
        "GROUPS_SELECT": "👉 На какую группу хочешь переключиться?",
        "GROUPS_WELCOME_ADMIN": "👋 Привет, админ! Готов управлять своей командой?",
        "GROUPS_WELCOME": "👋 Добро пожаловать в Allkinds! Введи код группы чтобы присоединиться.",
        "GROUPS_SWITCH_TO": "👉 Перейти в {group_name}.",
        "GROUPS_INVITE_LINK": "🎉 <b>{group_name}</b>\n{group_desc}\nПриглашение: {deeplink}\nКод: {invite_code}",
        "NEW_QUESTION_NOTIFICATION": "📩 Новый вопрос в очереди: {question_text}...",
        "QUEUE_LOAD_UNANSWERED": "📋 Готов ответить на вопросы из очереди?",
        "GROUPS_LEFT_SUCCESS": "👋 Вы успешно покинули группу.",
        "GROUPS_LEFT_ERROR": "😕 Ошибка при выходе из группы. Пожалуйста, попробуйте ещё раз.",
        "GROUPS_DELETED_SUCCESS": "🗑️ Группа успешно удалена.",
        "GROUPS_DELETED_ERROR": "😕 Ошибка при удалении группы. Пожалуйста, попробуйте ещё раз.",
        # --- Questions ---
        "QUESTION_TOO_SHORT": "😅 Вопрос слишком короткий... Попробуй ещё раз.",
        "QUESTION_MUST_JOIN_GROUP": "🔒 Сначала присоединись к группе, чтобы задавать вопросы.",
        "QUESTION_DUPLICATE": "🤔 Такой вопрос уже есть. Попробуй другой.",
        "QUESTION_REJECTED": "🚫 Этот вопрос не прошёл модерацию.",
        "QUESTION_ADDED": "🎉 Вопрос добавлен! +{points}💎 на твой счёт.",
        "QUESTION_PENDING_APPROVAL": "⏳ Твой вопрос отправлен на модерацию администратору.",
        "QUESTION_ADMIN_APPROVAL": "📝 Новый вопрос от {author_name}:\n\n{question_text}\n\nОдобрить или отклонить?",
        "QUESTION_APPROVED_ADMIN": "✅ Вопрос одобрен и отправлен участникам группы.",
        "QUESTION_REJECTED_ADMIN": "❌ Вопрос отклонён.",
        "QUESTION_APPROVED_AUTHOR": "✅ Твой вопрос одобрен! +{points}💎 на твой счёт.",
        "QUESTION_REJECTED_AUTHOR": "❌ Твой вопрос отклонён администратором.",
        "USER_BANNED_ADMIN": "🚫 Пользователь {banned_nickname} забанен и удалён из группы.",
        "USER_BANNED_NOTIFICATION": "🚫 Вы заблокированы в группе '{group_name}' за спам.",
        "USER_BANNED_JOIN_ATTEMPT": "🚫 Вы заблокированы в этой группе и не можете присоединиться.",
        "QUESTION_DELETED": "🗑 Вопрос удалён.",
        "QUESTION_ALREADY_DELETED": "🤷‍♂️ Этот вопрос уже исчез.",
        "QUESTION_ONLY_AUTHOR_OR_CREATOR": "🔒 Только ты или создатель можете это удалить.",
        "QUESTION_ANSWER_SAVED": "✅ Твой ответ сохранён.",
        "QUESTION_NO_ANSWERED": "🤔 Здесь пока нет вопросов. Задашь первый?",
        "QUESTION_MORE_ANSWERED": "⬇️ Больше отвеченных вопросов ниже:",
        "QUESTION_NO_MORE_ANSWERED": "🙌 Это все вопросы на данный момент.",
        "QUESTION_CAN_CHANGE_ANSWER": "✏️ Хочешь обновить свой ответ?",
        "QUESTION_INTERNAL_ERROR": "😕 Упс, неожиданная ошибка. Пожалуйста, попробуй снова.",
        "QUESTION_LOAD_ANSWERED": "⬇️ Загрузить отвеченные вопросы",
        "QUESTION_LOAD_MORE": "⬇️ Загрузить ещё",
        "QUESTION_DELETE": "🗑 Удалить",
        # --- Match ---
        "MATCH_NO_VALID": "🤔 Совпадений пока нет. Ответь ещё на несколько вопросов или задай свои!",
        "MATCH_FOUND": "🎉 {nickname}, {similarity}% ({common_questions} questions), {distance_info}\n{intro}",
        "MATCH_AI_CHEMISTRY": "💬 Начать приватный чат",
        "MATCH_SHOW_AGAIN": "🔁 Показать позже снова",
        "MATCH_DONT_SHOW": "🚫 Больше не показывать",
        "MATCH_PREV": "<<",
        "MATCH_NEXT": ">>",
        "MATCH_NOT_ENOUGH_POINTS": "❌ Недостаточно поинтов для просмотра следующего мэтча",
        "MATCH_NO_OTHERS": "В группе пока нет других участников для совпадений.",
        # --- Match Connection Messages ---
        "MATCH_REQUEST_SENT": "🔔 Мы уведомили {nickname} о твоём интересе. Мы дадим знать, когда они примут решение!",
        "MATCH_INCOMING_REQUEST": "🤝 {nickname} хочет связаться с тобой",
        "MATCH_REQUEST_ACCEPTED": "✅ {nickname} принял твой запрос на совпадение!",
        "MATCH_REQUEST_REJECTED": "😔 {nickname} отклонил твой запрос на совпадение.",
        "MATCH_REQUEST_BLOCKED": "🚫 {nickname} решил не общаться с тобой 😞",
        # --- System/General ---
        "INSTRUCTIONS_TEXT": (
            "🎯 Как работает Allkinds:\n\n"
            "❓ Задавай важные для тебя вопросы (+10💎)\n"
            "Просто напиши свой да/нет вопрос и отправь\n\n"
            "✅ Отвечай на вопросы других (+1💎)\n"
            "Каждый ответ помогает найти лучшие совпадения\n\n"
            "🔍 Найди лучшее совпадение (-5💎)\n"
            "Используй \"Кто резонирует\", чтобы увидеть кто подходит тебе больше всего\n\n"
            "🤝 Связывайся с теми, кто нравится\n"
            "Отправляй запросы на связь и обменивайтесь контактами\n\n"
            "💎 Зарабатывай поинты участием, трать их на поиск совпадений"
        ),
        # --- Buttons ---
        "BTN_CREATE_GROUP": "🌀 Запустить новую группу",
        "BTN_JOIN_GROUP": "🔑 Присоединиться по коду приглашения",
        "BTN_SWITCH_TO": "👉 Переключиться на {group_name}",
        "BTN_DELETE_GROUP": "🗑️ Удалить {group_name}",
        "BTN_LEAVE_GROUP": "👋 Покинуть {group_name}",
        "BTN_DELETE": "🗑 Удалить",
        "BTN_CANCEL": "❌ Отмена",
        "BTN_SEND_LOCATION": "📍 Поделиться своей локацией",
        "BTN_GENDER_MALE": "👨 Мужчина",
        "BTN_GENDER_FEMALE": "👩 Женщина",
        "BTN_LOOKING_FOR_MALE": "👨 Мужчину",
        "BTN_LOOKING_FOR_FEMALE": "👩 Женщину",
        "BTN_LOOKING_FOR_ALL": "👥 Всех",
        "BTN_WHO_IS_VIBING": "🔍 Кто сейчас резонирует больше всех",
        "BTN_CONNECT": "🤝 Связаться",
        "BTN_ACCEPT_MATCH": "✅ Принять",
        "BTN_REJECT_MATCH": "❌ Отклонить",
        "BTN_DECLINE_MATCH": "❌ Отклонить",
        "BTN_BLOCK_MATCH": "🚫 Заблокировать",
        "BTN_GO_TO_CHAT": "💬 Перейти в чат",
        "BTN_GOT_IT": "✅ Понятно",
        "NO_AVAILABLE_ANSWERED_QUESTIONS": "🫥 Ты отвечал на вопросы, но они были удалены — нечего пересматривать.",
        "UNANSWERED_QUESTIONS_MSG": "🕑 У тебя осталось <b>{count}</b> неотвеченных вопрос(ов).",
        "BTN_LOAD_UNANSWERED": "🔄 Загрузить неотвеченные вопросы",
        "TOKEN_EXPIRE_REMINDER": "⏳ Твой токен вот-вот истечёт. Нажми кнопку, чтобы продлить свой аккаунт.",
        "TOKEN_EXTEND": "🔄 Продлить",
        "TOKEN_EXTENDED": "✅ Твой токен был продлён.",
        "QUESTIONS_ALL_ANSWERED": "🎉 Это все вопросы на данный момент, возвращайся позже!",
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
ONBOARDING_SEND_INTRO = "ONBOARDING_SEND_INTRO"
ONBOARDING_INTRO_TOO_LONG = "ONBOARDING_INTRO_TOO_LONG"
ONBOARDING_SELECT_GENDER = "ONBOARDING_SELECT_GENDER"
ONBOARDING_SELECT_LOOKING_FOR = "ONBOARDING_SELECT_LOOKING_FOR"
ONBOARDING_SEND_LOCATION = "ONBOARDING_SEND_LOCATION"
ONBOARDING_LOCATION_REQUIRED = "ONBOARDING_LOCATION_REQUIRED"
ONBOARDING_LOCATION_SAVED = "ONBOARDING_LOCATION_SAVED"
ONBOARDING_COMPLETE = "ONBOARDING_COMPLETE"
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
GROUPS_LEFT_SUCCESS = "GROUPS_LEFT_SUCCESS"
GROUPS_LEFT_ERROR = "GROUPS_LEFT_ERROR"
GROUPS_DELETED_SUCCESS = "GROUPS_DELETED_SUCCESS"
GROUPS_DELETED_ERROR = "GROUPS_DELETED_ERROR"

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
MATCH_PREV = "MATCH_PREV"
MATCH_NEXT = "MATCH_NEXT"
MATCH_NOT_ENOUGH_POINTS = "MATCH_NOT_ENOUGH_POINTS"
MATCH_NO_OTHERS = "MATCH_NO_OTHERS"

# --- Match Connection Messages ---
MATCH_REQUEST_SENT = "MATCH_REQUEST_SENT"
MATCH_INCOMING_REQUEST = "MATCH_INCOMING_REQUEST"
MATCH_REQUEST_ACCEPTED = "MATCH_REQUEST_ACCEPTED"
MATCH_REQUEST_REJECTED = "MATCH_REQUEST_REJECTED"
MATCH_REQUEST_BLOCKED = "MATCH_REQUEST_BLOCKED"

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
BTN_GENDER_MALE = "BTN_GENDER_MALE"
BTN_GENDER_FEMALE = "BTN_GENDER_FEMALE"
BTN_LOOKING_FOR_MALE = "BTN_LOOKING_FOR_MALE"
BTN_LOOKING_FOR_FEMALE = "BTN_LOOKING_FOR_FEMALE"
BTN_LOOKING_FOR_ALL = "BTN_LOOKING_FOR_ALL"
BTN_WHO_IS_VIBING = "BTN_WHO_IS_VIBING"
BTN_CONNECT = "BTN_CONNECT"
BTN_ACCEPT_MATCH = "BTN_ACCEPT_MATCH"
BTN_REJECT_MATCH = "BTN_REJECT_MATCH"
BTN_DECLINE_MATCH = "BTN_DECLINE_MATCH" 
BTN_BLOCK_MATCH = "BTN_BLOCK_MATCH"
BTN_GO_TO_CHAT = "BTN_GO_TO_CHAT"
BTN_GOT_IT = "BTN_GOT_IT"

NO_AVAILABLE_ANSWERED_QUESTIONS = "NO_AVAILABLE_ANSWERED_QUESTIONS"

UNANSWERED_QUESTIONS_MSG = "UNANSWERED_QUESTIONS_MSG"
BTN_LOAD_UNANSWERED = "BTN_LOAD_UNANSWERED"

TOKEN_EXPIRE_REMINDER = "TOKEN_EXPIRE_REMINDER"
TOKEN_EXTEND = "TOKEN_EXTEND"
TOKEN_EXTENDED = "TOKEN_EXTENDED"

QUESTIONS_ALL_ANSWERED = "QUESTIONS_ALL_ANSWERED"

NEW_QUESTION_NOTIFICATION = "NEW_QUESTION_NOTIFICATION"
QUEUE_LOAD_UNANSWERED = "QUEUE_LOAD_UNANSWERED"

# Question moderation constants
QUESTION_PENDING_APPROVAL = "QUESTION_PENDING_APPROVAL"
QUESTION_ADMIN_APPROVAL = "QUESTION_ADMIN_APPROVAL"
QUESTION_APPROVED_ADMIN = "QUESTION_APPROVED_ADMIN"
QUESTION_REJECTED_ADMIN = "QUESTION_REJECTED_ADMIN"
QUESTION_APPROVED_AUTHOR = "QUESTION_APPROVED_AUTHOR"
QUESTION_REJECTED_AUTHOR = "QUESTION_REJECTED_AUTHOR"

# User ban constants
USER_BANNED_ADMIN = "USER_BANNED_ADMIN"
USER_BANNED_NOTIFICATION = "USER_BANNED_NOTIFICATION" 
USER_BANNED_JOIN_ATTEMPT = "USER_BANNED_JOIN_ATTEMPT" 