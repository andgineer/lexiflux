# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                   |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------- | -------: | -------: | ------: | --------: |
| lexiflux/apps.py                       |       14 |        0 |    100% |           |
| lexiflux/ebook/book\_base.py           |       72 |        7 |     90% |44, 51, 92, 129-132 |
| lexiflux/ebook/book\_epub.py           |       92 |        9 |     90% |94, 111, 114-116, 162, 176-178 |
| lexiflux/ebook/book\_plain\_text.py    |      106 |        4 |     96% |58-59, 128, 175 |
| lexiflux/ebook/headings.py             |       36 |        1 |     97% |       134 |
| lexiflux/ebook/page\_splitter.py       |       37 |        5 |     86% |     23-29 |
| lexiflux/language/google\_languages.py |       12 |        0 |    100% |           |
| lexiflux/language/translation.py       |       45 |        6 |     87% |     48-56 |
| lexiflux/models.py                     |      111 |       16 |     86% |41, 51, 93, 104, 113-114, 131, 142, 160, 217-229 |
| lexiflux/settings.py                   |        0 |        0 |    100% |           |
| lexiflux/signals.py                    |       13 |        0 |    100% |           |
| lexiflux/tests.py                      |        0 |        0 |    100% |           |
| lexiflux/urls.py                       |        3 |        0 |    100% |           |
| lexiflux/utils.py                      |        8 |        5 |     38% |     10-16 |
| lexiflux/views.py                      |      138 |       32 |     77% |25, 35, 54, 63, 141-143, 147, 176, 211-212, 223-248, 254-264 |
|                              **TOTAL** |  **687** |   **85** | **88%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/andgineer/lexiflux/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/andgineer/lexiflux/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fandgineer%2Flexiflux%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.