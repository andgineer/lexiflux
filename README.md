[![Build Status](https://github.com/andgineer/lexiflux/workflows/CI/badge.svg)](https://github.com/andgineer/lexiflux/actions)
[![Coverage](https://raw.githubusercontent.com/andgineer/lexiflux/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)
<br/><br/>
<img align="left" width="200" src="lexiflux/static/android-chrome-192x192.png" />

# Lexiflux

Reading foreign texts with dictionary.

<br clear="left"/>

![Alice in Wonderland](docs/includes/ponedeljak-pocinje-u-subotu.jpg)


## Quick start

You need [uv](https://github.com/astral-sh/uv) installed.

    . ./activete.sh  # note space between . and ./activate.sh
    ./manage createsuperuser  # create admin user
    make run

open in web-browser http://localhost:8000

## Scripts
    make help

## New installation
    make migrate
    ./manage createsuperuser

https://github.com/nidhaloff/deep-translator
https://github.com/terryyin/translate-python

## Allure test report

* [Allure report](https://andgineer.github.io/lexiflux/builds/tests/)

## Coverage report
* [Codecov](https://app.codecov.io/gh/andgineer/lexiflux/tree/main/src%2Fgarmin_daily)
* [Coveralls](https://coveralls.io/github/andgineer/lexiflux)
