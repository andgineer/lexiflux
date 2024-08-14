[![Build Status](https://github.com/andgineer/lexiflux/workflows/CI/badge.svg)](https://github.com/andgineer/lexiflux/actions)
[![Coverage](https://raw.githubusercontent.com/andgineer/lexiflux/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)
<br/><br/>
<img align="left" width="200" src="lexiflux/static/android-chrome-192x192.png" />

# Lexiflux

Master languages faster with our AI-powered reading companion. 

Instantly translate and understand foreign texts as you read, building your vocabulary and comprehension skills effortlessly.

<br clear="left"/>

![Alice in Wonderland](docs/includes/ponedeljak-pocinje-u-subotu.jpg)

## Quick start
You need to have [Docker](https://docs.docker.com/get-docker/) installed.

    docker start lexiflux > null 2>&1 || docker run -d -p 6100:8000 --name lexiflux andgineer/lexiflux

Open the lexiflux at http://localhost:6100

## AI Models
(!) To install in the docker local AI Ollama model add `OLLAMA_LOAD_MODEL=llama3` to the `docker run` command.

Please note it will download about 5Gb Ollama AI model and require about 6G RAM for the Docker container to run.

Alternatively you can use ChatGPT, Claude or other managed AI solutions. 
See [AI Settings](http://localhost:6100/ai-settings/) section.

## Local AI
Lexiflux use AI models to create Lexical Articles in Sidebar 
(you open it with blue binocular icon).

Also you can use AI for inline text translation. By default
it uses Google Translate.

To configure Sidebar and inline translation see `Language Preferences`.
There are separate settings for each language, so you can configure
different settings for different languages.

If you want to use free local AI, you need to install 
[Ollama](https://ollama.com/download/mac) and preload models.

    ollama pull llama3

This is already done in the Docker container (`OLLAMA_LOAD_MODEL=llama3` to the `docker run` to load the model).

But I recommend using paid [openAI](https://openai.com/index/openai-api/) 
or [Anthropic](https://www.anthropic.com/api-bk).

They are more accurate and faster.

For paid models you should sign up and get API key.
Place API key into appropriate environment variable.

    export OPENAI_API_KEY=...
    export ANTHROPIC_API_KEY=...

Or set appropriate fields in `AI Settings` section.

Note! If you configure using paid models, each time Lexiflux shows you the 
article in the Sidebar, you are charged by AI provider.

## Updates
To update you can use

    docker exec -it lexiflux ./manage update
    docker restart lexiflux

But keep in mind that as with any update, it may break something.
So it is better to make a backup before updating - see below.

## Backup / Restore the Docker container

### Backup
#### For Windows (PowerShell):
docker commit lexiflux lexiflux_backup
docker save lexiflux_backup -o lexiflux_backup.tar

#### For Linux/macOS:
docker commit lexiflux lexiflux_backup
docker save lexiflux_backup | gzip > lexiflux_backup.tar.gz

### Restore
#### For Windows (PowerShell):
docker stop lexiflux
docker rm lexiflux
docker load -i lexiflux_backup.tar
docker run -d -p 6100:8000 --name lexiflux lexiflux_backup

#### For Linux/macOS:
docker stop lexiflux
docker rm lexiflux
gunzip -c lexiflux_backup.tar.gz | docker load
docker run -d -p 6100:8000 --name lexiflux lexiflux_backup

## Build from sources
Clone [the repo](https://github.com/andgineer/lexiflux).

Install [uv](https://github.com/astral-sh/uv).

Install [invoke](https://docs.pyinvoke.org/en/stable/) preferably with 
[`pipx`](https://pypa.github.io/pipx/):

    pipx install invoke

Create development environment:

    . ./activete.sh  # note space between . and ./activate.sh
    invoke buildjs
    invoke init-db
    invoke run

open in web-browser http://localhost:8000

## Local SSL
Generate self-issued keys

    inv keygen

Run server with SSL

    inv runssl

If you want valid sertificate install mkcert. For macOS

    brew install mkcert

Install root certificate

    mkcert -install

Update `runssl` command in Makefile to use this certificates.

## Scripts
To get available scripts:

    inv --list

## Allure test report

* [Allure report](https://andgineer.github.io/lexiflux/builds/tests/)

## Coverage report
* [Codecov](https://app.codecov.io/gh/andgineer/lexiflux/tree/main/src%2Fgarmin_daily)
* [Coveralls](https://coveralls.io/github/andgineer/lexiflux)
