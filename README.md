# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                     |    Stmts |     Miss |   Cover |   Missing |
|----------------------------------------- | -------: | -------: | ------: | --------: |
| lexiflux/admin.py                        |        6 |        0 |    100% |           |
| lexiflux/api.py                          |       24 |        3 |     88% |     37-39 |
| lexiflux/apps.py                         |       14 |        0 |    100% |           |
| lexiflux/ebook/book\_base.py             |       71 |        5 |     93% |43, 50, 91, 130-131 |
| lexiflux/ebook/book\_epub.py             |       92 |        8 |     91% |94, 111, 114-116, 176-178 |
| lexiflux/ebook/book\_plain\_text.py      |      111 |        7 |     94% |58-59, 112-114, 135, 182 |
| lexiflux/ebook/headings.py               |       36 |        0 |    100% |           |
| lexiflux/ebook/page\_splitter.py         |       37 |        5 |     86% |     23-29 |
| lexiflux/forms.py                        |       33 |       18 |     45% |14-18, 35-51 |
| lexiflux/language/google\_languages.py   |       12 |        0 |    100% |           |
| lexiflux/language/sentence\_extractor.py |       51 |        6 |     88% |56-58, 86-87, 94 |
| lexiflux/language/translation.py         |       44 |        0 |    100% |           |
| lexiflux/language/word\_extractor.py     |       75 |        0 |    100% |           |
| lexiflux/lexical\_articles.py            |       10 |       10 |      0% |      3-32 |
| lexiflux/llm.py                          |      142 |      142 |      0% |     3-374 |
| lexiflux/models.py                       |      201 |       23 |     89% |70, 80, 133, 142-143, 160, 171, 192, 205, 235, 270, 272-273, 276, 352-353, 398-410 |
| lexiflux/settings.py                     |        0 |        0 |    100% |           |
| lexiflux/signals.py                      |       21 |        2 |     90% |     41-42 |
| lexiflux/tests.py                        |        0 |        0 |    100% |           |
| lexiflux/urls.py                         |        6 |        0 |    100% |           |
| lexiflux/utils.py                        |        8 |        0 |    100% |           |
| lexiflux/views.py                        |      343 |      128 |     63% |68, 75-80, 115, 134, 143, 212, 267-287, 337-361, 368-383, 390-396, 408-446, 451-464, 471-494, 499-513, 519-521, 534-535, 542-561, 596-597, 623 |
|                                **TOTAL** | **1337** |  **357** | **73%** |           |


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