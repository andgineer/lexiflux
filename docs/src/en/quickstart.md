# Quick start
You need to have [Docker](https://docs.docker.com/get-docker/) installed.

Open the terminal and run the following command:

    docker start lexiflux || docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

That's it! You have a running Lexiflux.

Open it in web browser at [http://localhost:6100](http://localhost:6100)

??? note "Docker says 'No such container: lexiflux'?"
    That's expected the first time. The command has two parts. `docker start lexiflux` starts your
    Lexiflux container, but the first time there is none yet, so Docker reports
    `No such container: lexiflux` and `failed to start containers: lexiflux`.

    Then the second part, `docker run`, downloads Lexiflux (Docker says
    `Unable to find image 'andgineer/lexiflux:latest' locally` and shows the download progress) and
    creates the container.

    From then on the same command just starts your container, without these messages.

Remember the DB with your books and reading progress is stored in the Docker container.
If you remove the container, you will lose all your data.

To backup your data, see the [Backup](docker.md#backup) section.

To update to the latest version, see the [Update](docker.md#updates) section.
