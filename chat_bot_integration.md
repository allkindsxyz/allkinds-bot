# Интеграция с Allkinds Chat Bot

## 1. Параметры для передачи в чат-бот

```python
# Формат ссылки
https://t.me/{ALLKINDS_CHAT_BOT_USERNAME}?start=match_{user_id}_{match_user_id}

# Где:
user_id - telegram_user_id инициатора чата
match_user_id - telegram_user_id мэтча
```

## 2. Данные из базы данных для чат-бота

```sql
-- Получение информации о мэтче
SELECT 
    gm1.nickname as initiator_nickname,
    gm1.photo_url as initiator_photo,
    gm2.nickname as match_nickname,
    gm2.photo_url as match_photo,
    g.name as group_name,
    g.id as group_id
FROM group_members gm1
JOIN group_members gm2 ON gm2.group_id = gm1.group_id
JOIN groups g ON g.id = gm1.group_id
WHERE 
    gm1.user_id = (SELECT id FROM users WHERE telegram_user_id = :initiator_id)
    AND gm2.user_id = (SELECT id FROM users WHERE telegram_user_id = :match_id)
    AND gm1.group_id = gm2.group_id;
```

## 3. Константы для чат-бота

```python
POINTS_TO_CONNECT = 10  # Стоимость перехода в чат
MIN_ANSWERS_FOR_MATCH = 5  # Минимум ответов для мэтча
```

## 4. Структура базы данных

```sql
-- Таблица для статусов мэтчей
CREATE TABLE match_statuses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    match_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(16) NOT NULL,  -- 'hidden' | 'postponed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, group_id, match_user_id)
);
```

## 5. Параметры подключения к БД

```python
POSTGRES_USER = 'allkinds'
POSTGRES_PASSWORD = 'allkinds'
POSTGRES_DB = 'allkinds'
POSTGRES_HOST = 'localhost'  # Изменить на продакшн хост
POSTGRES_PORT = 5432
```

## 6. Двухэтапная логика матчинга (Two-Stage Matching)

### Описание
Система использует двухэтапный процесс подтверждения матчей вместо прямого перехода в чат-бот.

### Процесс
1. **Инициация**: Пользователь A нажимает "Connect" у матча
2. **Уведомление**: Пользователь B получает:
   - Сообщение: "{nickname} хочет подключиться к вам"
   - Карточку матча с фото и информацией
   - Три кнопки: "Принять", "Отклонить", "Заблокировать"
3. **Обратная связь**: Пользователь A получает уведомление о решении

### Статусы в MatchStatus
- `pending_approval` - Ожидание решения от второго пользователя
- `accepted` - Запрос принят, создается Match запись
- `rejected` - Запрос отклонен
- `blocked` - Пользователь заблокирован (+ обратная запись с `hidden`)

### Исключения в find_best_match
Функция исключает пользователей со статусами:
- `hidden`, `postponed` (старые)
- `pending_approval`, `rejected`, `blocked` (новые)

### Новые сообщения
```python
MATCH_REQUEST_SENT = "🔔 Мы уведомили {nickname} о вашем интересе..."
MATCH_INCOMING_REQUEST = "💌 {nickname} хочет подключиться к вам"
MATCH_REQUEST_ACCEPTED = "✅ {nickname} принял ваш запрос..."
MATCH_REQUEST_REJECTED = "😔 {nickname} отклонил ваш запрос..."
MATCH_REQUEST_BLOCKED = "🚫 {nickname} решил не общаться с вами 😞"

BTN_ACCEPT_MATCH = "✅ Принять"
BTN_REJECT_MATCH = "❌ Отклонить"  
BTN_BLOCK_MATCH = "🚫 Заблокировать"
BTN_GO_TO_CHAT = "💬 Перейти в чат"
```

### Новые хэндлеры
- `cb_accept_match` - Принятие запроса на матч
- `cb_reject_match` - Отклонение запроса на матч  
- `cb_block_match` - Блокировка пользователя

### Изменения в cb_match_chat
- Теперь создает `MatchStatus` с `pending_approval`
- Отправляет уведомление второму пользователю
- Не создает сразу `Match` запись

## 7. Обработка ошибок

- Проверка существования пользователей
- Проверка наличия мэтча в БД
- Проверка статуса мэтча (hidden/postponed)
- Обработка случая, когда у пользователя недостаточно баллов

## 8. Дополнительная информация

- Чат-бот должен использовать ту же базу данных, что и основной бот
- Все операции с баллами и статусами мэтчей должны быть атомарными
- Необходимо обеспечить консистентность данных между ботами 