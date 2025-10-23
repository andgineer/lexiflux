[![Build Status](https://github.com/andgineer/lexiflux/workflows/CI/badge.svg)](https://github.com/andgineer/lexiflux/actions)
[![Coverage](https://raw.githubusercontent.com/andgineer/lexiflux/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)
<br/><br/>
<img align="left" width="200" src="lexiflux/static/android-chrome-192x192.png" />

# Lexiflux reader

Master languages faster with our AI-powered reading companion.

Instantly translate and understand foreign texts as you read, building your vocabulary and comprehension skills effortlessly.

<br clear="left"/>

![Lexiflux](docs/src/en/images/ponedeljak.png)

## Quick start

[Lexiflux Quick start](https://lexiflux.sorokin.engineer/quickstart/)

## Docker image

[Docker image](https://hub.docker.com/r/andgineer/lexiflux)

## Developers
### Build from sources
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

### Local SSL
Generate self-issued keys

    inv keygen

Run server with SSL

    inv runssl

If you want valid sertificate install mkcert. For macOS

    brew install mkcert

Install root certificate

    mkcert -install

Update `runssl` command in `tasks.py` to use this certificates.

### Scripts
To get available scripts:

    inv --list

### Allure test report

* [Allure report](https://andgineer.github.io/lexiflux/builds/tests/)

### Coverage report

* [Coveralls](https://coveralls.io/github/andgineer/lexiflux)
