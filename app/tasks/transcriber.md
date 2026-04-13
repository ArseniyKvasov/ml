### Текущие проблемы

- Язык транскрибации жестко закодирован (`language="ru"`)

- Нет автоопределения языка

- Нет четкого протокола: смешаны текстовые логи и бинарные аудио данные

- Отправляется финальное `full_text` сообщение (не нужно)

### Требования к WebSocket `/transcriber/ws/transcribe`

**1. Handshake (инициализация)**

- Ожидать первое сообщение от клиента в формате JSON:

```JSON
{"type": "init", "config": {"language": null}}
```


- `language: null` означает автоопределение языка (передать `None` в `model.transcribe`)

- Ответить:

```JSON
{"type": "init_ack", "status": "ready", "session_id": "<uuid>"}
```


**2. Прием аудио**

- Все бинарные сообщения (bytes) накапливать во временный файл

- Игнорировать любые другие текстовые сообщения, которые не являются валидными JSON командами

**3. Поддержка команд (JSON)**

|Команда|Действие|
|-|-|
|`{"type": "end"}`|Завершить прием аудио, начать транскрибацию|
|`{"type": "ping"}`|Ответить `{"type": "pong"}`|
|`{"type": "cancel"}`|Ответить `{"type": "cancel_ack"}` и закрыть соединение|

**4. Отправка результатов (после получения `end`)**

- Сначала отправить информацию о детектированном языке:

```JSON
{"type": "language_info", "detected_language": "en", "confidence": 0.98}
```


- Затем каждый сегмент транскрипции отправлять отдельным JSON сообщением по мере готовности:

```JSON
{"type": "transcript", "start_ms": 0, "end_ms": 2500, "text": "Hello world", "is_final": true}
```


- После отправки последнего сегмента закрыть WebSocket соединение с кодом 1000

- **НЕ отправлять** финальное сообщение с `full_text`

**5. Обработка ошибок**

При любой ошибке отправить JSON и закрыть соединение:

```JSON
{"type": "error", "code": "WHISPER_ERROR|TIMEOUT|NO_AUDIO", "message": "описание ошибки"}
```


**6. Healthcheck (HTTP)**

- Добавить эндпоинт `GET /transcriber/health`

- Ответ:

```JSON
{"status": "healthy", "model": "small", "auto_language": true}
```


### Критерии приемки

- Автоопределение языка работает (при `language: null`)

- При явном указании языка (например `"language": "en"`) используется указанный язык

- JSON и бинарные сообщения не смешиваются (текст = команды, bytes = аудио)

- Транскрипция отправляется по чанкам, нет финального `complete` сообщения

- Все ошибки возвращаются в JSON формате

- Соединение корректно закрывается после отправки последнего чанка

### Форматы сообщений (исходящий поток)

|Тип|Пример|
|-|-|
|`init_ack`|`{"type":"init_ack","status":"ready","session_id":"123"}`|
|`language_info`|`{"type":"language_info","detected_language":"en","confidence":0.98}`|
|`transcript`|`{"type":"transcript","start_ms":0,"end_ms":2500,"text":"Hello","is_final":true}`|
|`pong`|`{"type":"pong"}`|
|`cancel_ack`|`{"type":"cancel_ack","status":"cancelled"}`|
|`error`|`{"type":"error","code":"WHISPER_ERROR","message":"..."}`|

---

### Комментарий

Убрать `language="ru"`, поставить `language=None`. Убрать отправку финального `full_text`. Все эндпоинты теперь находятся в пространстве `/transcriber/`. WebSocket доступен по пути `/transcriber/ws/transcribe`. Healthcheck по пути `/transcriber/health`.

Установи faster whisper локально + Docker


