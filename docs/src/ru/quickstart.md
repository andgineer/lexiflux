# Быстрый старт
Вам нужно иметь установленный [Docker](https://docs.docker.com/get-docker/).

    docker start lexiflux > null 2>&1 || docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

Откройте lexiflux по адресу [http://localhost:6100](http://localhost:6100)

Вот и всё! У вас запущен экземпляр Lexiflux.

Помните, что база данных с вашими книгами и прогрессом чтения хранится в Docker контейнере. 
Если вы удалите контейнер, вы потеряете все свои данные.

Чтобы создать резервную копию ваших данных, обратитесь к разделу [Резервное копирование](docker.md#backup).
