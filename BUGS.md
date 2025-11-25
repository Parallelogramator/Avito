## BUG-01 — createdAt возвращается в невалидном формате

**ID:** BUG-01
**Severity:** High
**Priority:** High
**Title:** Поле `createdAt` содержит дублированное смещение времени (+0300 +0300)
**Environment:**
`https://qa-internship.avito.com/api/1/item` (v1)

**Steps to Reproduce:**

1. Выполнить запрос `POST /item` с валидным телом.
2. Выполнить запрос `GET /item/{id}`.
3. Проверить поле `createdAt`.

**Expected Result:**
Дата в формате:
`YYYY-MM-DDThh:mm:ss+03:00`

**Actual Result:**
`2025-11-26T01:18:06.758 +0300 +0300`

**Attachments:**
— Пример ответа сервера.

---

## BUG-02 — Некорректная схема ошибки 404 в API v2

**ID:** BUG-02
**Severity:** Medium
**Priority:** Medium
**Title:** Поле `result` возвращает объект вместо строки
**Environment:**
`GET /api/2/statistic/{id}`

**Steps:**

1. Отправить запрос на несуществующий ID.
2. Посмотреть структуру ошибки.

**Expected:**
`"result": "error text string"`

**Actual:**
`"result": { "message": "..." }`

---

## BUG-03 — Spoofing: клиент может накрутить статистику объявления (likes, viewCount)

**ID:** BUG-03
**Severity:** Critical
**Priority:** Highest
**Title:** API доверяет клиенту и сохраняет переданные значения статистики
**Environment:**
`POST /api/1/item`

**Steps:**

1. Создать объявление с телом:

```
{
  "name": "Test",
  "price": 1,
  "statistics": {
    "likes": 999999,
    "viewCount": 999999,
    "contacts": 999999
  }
}
```

2. Выполнить `GET /item/{id}`.

**Expected:**
Сервер должен игнорировать статистику от клиента и всегда выставлять `likes = 0`, `viewCount = 0`.

**Actual:**
Объявление создаётся с лайками 999999 и счётчиками просмотров 999999.

---

## BUG-04 — `POST /item` нарушает контракт API и не возвращает созданный объект

**ID:** BUG-04
**Severity:** High
**Priority:** High
**Title:** API возвращает текст вместо JSON-объекта созданного товара
**Environment:**
`POST /api/1/item`

**Steps:**

1. Создать товар.
2. Проверить тело ответа.

**Expected:**
JSON:

```
{
  "id": "<uuid>",
  "name": "...",
  "price": ...
}
```

**Actual:**

```
{"status": "Сохранили объявление - <UUID>"}
```

---

## BUG-05 — Нет заголовка Allow при 405 Method Not Allowed

**ID:** BUG-05
**Severity:** Low
**Priority:** Low
**Title:** Сервер не возвращает заголовок `Allow`
**Environment:**
Любой endpoint, запрос неправильным методом.

**Expected:**
`Allow: GET, POST`

**Actual:**
Заголовок отсутствует.

---

## BUG-06 — API позволяет создать товар с именем из одних пробелов

**ID:** BUG-06
**Severity:** Medium
**Priority:** Medium
**Title:** Валидация имени отсутствует — можно создать товар с пустым именем (строка из пробелов)
**Environment:**
`POST /api/1/item`

**Steps:**

1. Отправить JSON:

    ```
    {
      "name": "     ",
      "price": 1
    }
    ```

2. Выполнить `POST`.

    **Expected:**
    400 Bad Request.
    
    **Actual:**
    200 OK + объект создан.
