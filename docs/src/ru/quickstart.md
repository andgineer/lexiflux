# Быстрый старт
Вам нужно иметь установленный [Docker](https://docs.docker.com/get-docker/).

После этого откройте терминал и выполните следующую команду:

    docker start lexiflux || docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

Вот и всё! У вас запущен экземпляр Lexiflux.

Откройте его в браузере [http://localhost:6100](http://localhost:6100)

??? note "Docker пишет 'No such container: lexiflux'?"
    При первом запуске так и должно быть. Команда состоит из двух частей. `docker start lexiflux`
    запускает ваш контейнер Lexiflux, но в первый раз его ещё нет, поэтому Docker сообщает
    `No such container: lexiflux` и `failed to start containers: lexiflux`.

    Тогда вторая часть, `docker run`, скачивает Lexiflux (Docker пишет
    `Unable to find image 'andgineer/lexiflux:latest' locally` и показывает ход загрузки) и
    создаёт контейнер.

    В следующие разы та же команда просто запускает ваш контейнер, без этих сообщений.

Помните, что база данных с вашими книгами и прогрессом чтения хранится в Docker контейнере.
Если вы удалите контейнер, вы потеряете все свои данные.

Чтобы создать резервную копию ваших данных, обратитесь к разделу [Резервное копирование](docker.md#backup).

Чтобы обновиться до последнего релиза - [Обновления](docker.md#updates).
