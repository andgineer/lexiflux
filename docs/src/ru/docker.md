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

### Локальный Ollama AI {#local-ollama-ai}
Если вы хотите использовать бесплатный локальный AI и у вас достаточно оперативной памяти, вы можете предварительно загрузить модель [Ollama](aimodels.md#ollama)
в docker.

Добавьте `OLLAMA_LOAD_MODEL=llama3` к команде `docker run`.

Обратите внимание, что это загрузит около 5 ГБ модели Ollama AI и потребует около 6 ГБ оперативной памяти для работы Docker контейнера.

## Обновления {#updates}
Для обновления вы можете использовать

    docker exec -it lexiflux ./manage update
    docker restart lexiflux

Но имейте в виду, что, как и с любым обновлением, оно может что-то сломать.
Поэтому лучше сделать [резервную копию](docker.md#backup) перед обновлением.

## Резервное копирование {#backup}
Чтобы создать архив с полной резервной копией вашего Docker контейнера Lexiflux.

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

## Восстановление

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
