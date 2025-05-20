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

## 6. Процесс работы

1. Пользователь нажимает "Go to chat" в основном боте
2. Списываются POINTS_TO_CONNECT баллов
3. Создается запись в match_statuses
4. Формируется ссылка с параметрами
5. При переходе в чат-бот, он должен:
   - Получить информацию о мэтче из БД
   - Показать информацию о совпадении (similarity, common questions)
   - Создать приватный чат между пользователями

## 7. Обработка ошибок

- Проверка существования пользователей
- Проверка наличия мэтча в БД
- Проверка статуса мэтча (hidden/postponed)
- Обработка случая, когда у пользователя недостаточно баллов

## 8. Дополнительная информация

- Чат-бот должен использовать ту же базу данных, что и основной бот
- Все операции с баллами и статусами мэтчей должны быть атомарными
- Необходимо обеспечить консистентность данных между ботами 