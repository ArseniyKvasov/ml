**Контекст:** ML сервис должен принимать транскрипт лекции и возвращать тест для проверки знаний.

**API endpoint (HTTP):**

```JSON
POST /test/generate
GET  /test/health
```


**Формат запроса `/test/generate`:**

```JSON
{
  "transcript": [
    {"start_ms": 0, "text": "Hello world"},
    {"start_ms": 2500, "text": "This is a lecture about LU decomposition"}
  ],
  "num_questions": 10
}
```


**Формат ответа (успех):**

```JSON
{
  "status": "success",
  "test": [
    {
      "question_id": 1,
      "question_text": "Какая из следующих матриц может быть представлена в виде $A = LU$?",
      "question_type": "multiple_choice",
      "options": [
        "$\\begin{pmatrix} 1 & 2 \\\\ 2 & 1 \\end{pmatrix}$",
        "$\\begin{pmatrix} 0 & 1 \\\\ 1 & 1 \\end{pmatrix}$"
      ],
      "correct_answer": 0,
      "explanation": "Матрица имеет ненулевые главные миноры...",
      "subtopic": "Условия существования LU-разложения"
    },
    {
      "question_id": 2,
      "question_text": "Объясните алгоритм получения LU-разложения методом Гаусса.",
      "question_type": "open_ended",
      "options": null,
      "correct_answer": "Алгоритм заключается в последовательном исключении элементов под главной диагональю...",
      "explanation": "Это прямой ход метода Гаусса...",
      "subtopic": "Алгоритм нахождения LU-разложения"
    }
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
Ты — эксперт по созданию тестов для проверки знаний на основе лекции.

На основе транскрипта лекции создай тест из {num_questions} вопросов.

Правила:
1. Вопросы должны покрывать ключевые темы лекции
2. Типы вопросов: multiple_choice (70%) и open_ended (30%)
3. Для multiple_choice: 4 варианта ответа, только один правильный
4. Для open_ended: правильный ответ — развернутое объяснение (2-3 предложения)
5. Если в лекции есть формулы — используй LaTeX: \( E = mc^2 \)
6. Добавь пояснение (explanation) к каждому вопросу
7. Добавь subtopic — к какой теме лекции относится вопрос

Формат ответа ТОЛЬКО JSON массив:
[
  {
    "question_id": 1,
    "question_text": "текст вопроса",
    "question_type": "multiple_choice",
    "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"],
    "correct_answer": 0,
    "explanation": "пояснение",
    "subtopic": "тема"
  },
  ...
]

Для open_ended поле options = null, correct_answer = "развернутый ответ"

Транскрипт лекции:
{transcript_text}
```


3. Распарсить ответ LLM в JSON массив

4. Валидировать структуру (каждый элемент имеет все обязательные поля)

5. Вернуть результат

**Healthcheck `/test/health`:**

```JSON
{
  "status": "healthy",
  "llm_available": true
}
```


