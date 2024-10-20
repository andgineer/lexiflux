# AI модели

Lexiflux использует AI модели для создания `Лексических статей` в `Боковой панели`
(вы можете открыть её с помощью синей иконки бинокля).

Также вы можете использовать AI для встроенного перевода текста. По умолчанию
используется Google Translate.

Чтобы настроить Боковую панель и встроенный перевод, смотрите [Языковые настройки](http://localhost:6100/language-preferences/).
Для каждого языка есть отдельные настройки, поэтому вы можете настроить
разные параметры для разных языков.

## Типы лексических статей

### Работающие на AI (Translate, Lexical, Explain, Sentence)
Они используют предопределенные запросы для генерации статей.
Вы можете выбрать AI модель (ChatGPT, Claude и др.) для их выполнения.

#### Пользовательский AI
С типом "AI" вы можете определить свой собственный промпт для AI модели.

### Словарь
Встроено несколько словарей, таких как Google Translate, Linguee Translator, MyMemory Translator, PONS Translator.

### Сайт
Вы определяете URL для открытия и с какими параметрами.
Это полезно для хороших переводчиков, у которых нет API. Например, glosbe.com.

Большинство из них должны открываться во внешнем окне, но некоторые могут даже открываться внутри боковой панели.

Это контролируется параметром `open in new window`.

## OpenAI (ChatGPT), Anthropic (Claude) и другие

Для использования коммерческих AI провайдеров вам нужен `API KEY`.

Смотрите раздел [Настройки AI](http://localhost:6100/ai-settings/), чтобы узнать, как получить ключ для разных AI провайдеров.

## Ollama
Вы можете [установить](docker.md#local-ollama-ai) в docker локальную AI модель [Ollama](https://github.com/jmorganca/ollama).

Она бесплатная, но требует около 6 ГБ оперативной памяти для работы. Помните, что это оперативная память для контейнера Docker, а не для хост-машины.

И она не очень точная.