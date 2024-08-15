# Quick start
You need to have [Docker](https://docs.docker.com/get-docker/) installed.

    docker start lexiflux > null 2>&1 || docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

Open the lexiflux at [http://localhost:6100](http://localhost:6100)

That's it! You have a running instance of Lexiflux.

Remember the DB with your books and reading progress is stored in the Docker container. 
If you remove the container, you will lose all your data.

To backup your data, see the [Backup](docker.md#backup) section.
