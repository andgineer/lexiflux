# Lexiflux in Docker

## Installation

You always can use this magic command to start Lexiflux in Docker:

    docker start lexiflux > null 2>&1 || docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

If you want to know details, read below.
But you don't have to - the magic command above is all you need.

### Starting Lexiflux Docker Container
First part of the command `docker start lexiflux` tries to start the container with the name `lexiflux`.

In fact this is all that you need after initial container creation.

### Creating Lexiflux Docker Container
If first part of the command fails, the second part of the command

    docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

downloads the image `andgineer/lexiflux` from the Docker Hub,
creates a new container with the name `lexiflux` and exposes port `6100` on your host machine.

### AI keys
AI articles need API keys, which you give to the container as environment variables
(see [Keys](aimodels.md#keys) for which keys there are).
Put them in a file, one `NAME=value` per line, for example `lexiflux.env`:

    GEMINI_API_KEY=...
    GROQ_API_KEY=...
    OPENAI_API_KEY=...

and add `--env-file lexiflux.env` to the command that creates the container:

    docker run -d -p 6100:8000 --env-file lexiflux.env --name lexiflux andgineer/lexiflux

Keys are set when the container is created. The container also holds your books, so to
change the keys of an existing container make a [backup](docker.md#backup) and
[restore](docker.md#restore) it with `--env-file lexiflux.env` added to the `docker run` command.

### Configuration

#### Allowed Hosts

By default, the Docker container allows connections from any hostname (`*`). If you need to restrict access to specific hostnames, you can use the `LEXIFLUX_ALLOWED_HOSTS` environment variable:

```bash
docker run -d -p 6100:8000 -e LEXIFLUX_ALLOWED_HOSTS="localhost,example.com" --name lexiflux andgineer/lexiflux
```

The value should be a comma-separated list of hostnames. This will replace the default `*` setting.

## Stopping Lexiflux Docker Container
To stop the container you can use

    docker stop lexiflux

## Updates
To update you can use

    docker exec -it lexiflux ./manage update
    docker restart lexiflux

But keep in mind that as with any update, it may break something.
So it is better to make a [backup](docker.md#backup) before updating.

## Backup
To create archive with full backup of your Lexiflux Docker container.

The archive also contains the API keys passed to the container with `--env-file`, so do not share it.

=== "Linux/macOS"
    Enter in the terminal:

    ```bash
    docker commit lexiflux lexiflux_backup
    docker save lexiflux_backup | gzip > lexiflux_backup.tar.gz
    ```

=== "Windows (PowerShell)"
    In the command prompt, type:

    ```bash
    docker commit lexiflux lexiflux_backup
    docker save lexiflux_backup -o lexiflux_backup.tar
    ```

## Restore

To delete current container and create new one from archive created on the Backup stage.

Remember, you will lose all your data in the current container.

!!! danger "Warning"
    Again: all your books and reading progress in current container will be lost.
    We restore to the state that you saved on the Backup stage.

=== "Linux/macOS"
    Enter in the terminal:

    ```bash
    docker stop lexiflux
    docker rm lexiflux
    gunzip -c lexiflux_backup.tar.gz | docker load
    docker run -d -p 6100:8000 --name lexiflux lexiflux_backup
    ```

=== "Windows (PowerShell)"
    In the command prompt, type:

    ```bash
    docker stop lexiflux
    docker rm lexiflux
    docker load -i lexiflux_backup.tar
    docker run -d -p 6100:8000 --name lexiflux lexiflux_backup
    ```
