# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                   |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------- | -------: | -------: | ------: | --------: |
| lexiflux/apps.py                       |       14 |        0 |    100% |           |
| lexiflux/ebook/book\_base.py           |       70 |       23 |     67% |42, 49, 90, 95-100, 109-134 |
| lexiflux/ebook/book\_epub.py           |       45 |       45 |      0% |      2-98 |
| lexiflux/ebook/book\_plain\_text.py    |      126 |       19 |     85% |61-62, 67-73, 187, 208, 227-237 |
| lexiflux/ebook/headings.py             |       36 |        0 |    100% |           |
| lexiflux/language/google\_languages.py |       12 |        0 |    100% |           |
| lexiflux/language/translation.py       |       47 |       16 |     66% |20-24, 29, 35-37, 47-55, 79 |
| lexiflux/models.py                     |      104 |       34 |     67% |16-18, 35, 45, 73-75, 80, 85, 89-103, 107-109, 113, 124, 142, 182-206 |
| lexiflux/settings.py                   |        0 |        0 |    100% |           |
| lexiflux/signals.py                    |       13 |        3 |     77% | 21-22, 32 |
| lexiflux/tests.py                      |        0 |        0 |    100% |           |
| lexiflux/urls.py                       |        3 |        3 |      0% |       2-6 |
| lexiflux/utils.py                      |        8 |        8 |      0% |      2-15 |
| lexiflux/views.py                      |      126 |      126 |      0% |     2-250 |
|                              **TOTAL** |  **604** |  **277** | **54%** |           |


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