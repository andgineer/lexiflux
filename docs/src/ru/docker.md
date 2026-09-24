# Lexiflux в Docker

## Установка

Вы всегда можете использовать эту волшебную команду для запуска Lexiflux в Docker:

    docker start lexiflux > null 2>&1 || docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

Если вы хотите узнать подробности, читайте ниже.
Но вам не обязательно - волшебная команда выше это всё, что вам нужно.

### Запуск Docker контейнера Lexiflux
Первая часть команды `docker start lexiflux` пытается запустить контейнер с именем `lexiflux`.

На самом деле это всё, что вам нужно после первоначального создания контейнера.

### Создание Docker контейнера Lexiflux
Если первая часть команды не удалась, вторая часть команды

    docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

загружает образ `andgineer/lexiflux` из Docker Hub,
создает новый контейнер с именем `lexiflux` и открывает порт `6100` на вашей хост-машине.

### Ключи для AI {#ai-keys}
Для AI-статей нужны API-ключи, которые передаются контейнеру как переменные окружения
(какие бывают ключи, смотрите в разделе [Ключи](aimodels.md#keys)).
Запишите их в файл, по одному `ИМЯ=значение` в строке, например `lexiflux.env`:

    GEMINI_API_KEY=...
    GROQ_API_KEY=...
    OPENAI_API_KEY=...

и добавьте `--env-file lexiflux.env` к команде, которая создаёт контейнер:

    docker run -d -p 6100:8000 --env-file lexiflux.env --name lexiflux andgineer/lexiflux

Ключи задаются при создании контейнера. В контейнере хранятся и ваши книги, поэтому чтобы
поменять ключи существующего контейнера, сделайте [резервную копию](docker.md#backup) и
[восстановите](docker.md#restore) её, добавив `--env-file lexiflux.env` к команде `docker run`.

### Конфигурация

#### Разрешенные хосты

По умолчанию Docker контейнер разрешает подключения с любого имени хоста (`*`). Если вам нужно ограничить доступ к определенным именам хостов, вы можете использовать переменную окружения `LEXIFLUX_ALLOWED_HOSTS`:

```bash
docker run -d -p 6100:8000 -e LEXIFLUX_ALLOWED_HOSTS="localhost,example.com" --name lexiflux andgineer/lexiflux
```

Значение должно быть списком имен хостов, разделенных запятыми. Это заменит настройку по умолчанию `*`.

## Остановка Docker контейнера Lexiflux
Для остановки контейнера вы можете использовать

    docker stop lexiflux

## Обновления {#updates}
Для обновления вы можете использовать

    docker exec -it lexiflux ./manage update
    docker restart lexiflux

Но имейте в виду, что, как и с любым обновлением, оно может что-то сломать.
Поэтому лучше сделать [резервную копию](docker.md#backup) перед обновлением.

## Резервное копирование {#backup}
Чтобы создать архив с полной резервной копией вашего Docker контейнера Lexiflux.

Архив содержит и API-ключи, переданные контейнеру через `--env-file`, поэтому не передавайте его другим.

=== "Linux/macOS"
    Введите в терминале:

    ```bash
    docker commit lexiflux lexiflux_backup
    docker save lexiflux_backup | gzip > lexiflux_backup.tar.gz
    ```

=== "Windows (PowerShell)"
    В командной строке введите:

    ```bash
    docker commit lexiflux lexiflux_backup
    docker save lexiflux_backup -o lexiflux_backup.tar
    ```

## Восстановление {#restore}

Чтобы удалить текущий контейнер и создать новый из архива, созданного на этапе резервного копирования.

Помните, вы потеряете все свои данные в текущем контейнере.

!!! danger "Предупреждение"
    Еще раз: все ваши книги и прогресс чтения в текущем контейнере будут потеряны.
    Мы восстанавливаем состояние, которое вы сохранили на этапе резервного копирования.

=== "Linux/macOS"
    Введите в терминале:

    ```bash
    docker stop lexiflux
    docker rm lexiflux
    gunzip -c lexiflux_backup.tar.gz | docker load
    docker run -d -p 6100:8000 --name lexiflux lexiflux_backup
    ```

=== "Windows (PowerShell)"
    В командной строке введите:

    ```bash
    docker stop lexiflux
    docker rm lexiflux
    docker load -i lexiflux_backup.tar
    docker run -d -p 6100:8000 --name lexiflux lexiflux_backup
    ```
