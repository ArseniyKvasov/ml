**Контекст:** ML сервис (хост `vm4116226.firstbyte.club`) должен принимать транскрипт и возвращать структурированный конспект, используя внешний LLM API.

**API endpoint (HTTP):**

text

```JSON
POST /summary/summarize
GET  /summary/health
```


**Формат запроса `/summary/summarize`:**

```JSON
{
  "transcript": [
    {"start_ms": 0, "text": "Hello world"},
    {"start_ms": 2500, "text": "This is a lecture about physics"}
  ]
}
```


**Формат ответа (успех):**

json

```JSON
{
  "status": "success",
  "summary": [
    {"subtopic": "Введение", "content": "Лекция начинается с приветствия..."},
    {"subtopic": "Основные понятия", "content": "В физике существует понятие массы \\( m \\)..."}
  ]
}
```


**Формат ответа (ошибка):**

```JSON
{
  "status": "error",
  "code": "LLM_UNAVAILABLE|INVALID_INPUT|TIMEOUT",
  "message": "Описание ошибки"
}
```


**Логика работы:**

1. Склеить все сегменты транскрипта в единый текст

2. Отправить запрос к внешнему LLM API:

  - URL: `http://vm4120209.firstbyte.club/generate`

  - Headers: `X-API-Key: QbxxPuE5IVbNvvUFggsw37MFVyMHgM8p`

  - Model: `llama-3.1-8b-instant`

  - Prompt:

```JSON
Ты — ассистент, который составляет структурированный конспект лекции.

Правила:
1. Разбей конспект на логические подтемы (от 3 до 10)
2. Каждая подтема должна иметь заголовок (subtopic) и содержание (content)
3. Если в тексте есть математические формулы или физические выражения — используй LaTeX: \( E = mc^2 \) или \[ \int x^2 dx \]
4. Конспект должен быть кратким, но информативным

Формат ответа ТОЛЬКО JSON:
[{"subtopic": "...", "content": "..."}, ...]

Транскрипт лекции:
{transcript_text}
```


3. Распарсить ответ LLM в JSON массив

4. Валидировать структуру (каждый элемент имеет `subtopic` и `content`)

5. Вернуть результат

**Healthcheck `/summary/health`:**

```JSON
{
  "status": "healthy",
  "llm_available": true
}
```
