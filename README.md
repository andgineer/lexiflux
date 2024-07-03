# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                   |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------- | -------: | -------: | ------: | --------: |
| lexiflux/api.py                        |       24 |        7 |     71% |     32-39 |
| lexiflux/apps.py                       |       14 |        0 |    100% |           |
| lexiflux/ebook/book\_base.py           |       72 |       31 |     57% |36-37, 44, 51, 58-92, 96-106, 131-132 |
| lexiflux/ebook/book\_epub.py           |       92 |       35 |     62% |28-40, 49-61, 68-88, 94, 111, 114-116, 170, 176-178 |
| lexiflux/ebook/book\_plain\_text.py    |      111 |       75 |     32% |43-46, 55-60, 66-75, 79-99, 104-107, 112-114, 121-145, 149-159, 166-188 |
| lexiflux/ebook/headings.py             |       36 |       24 |     33% |19-31, 37-116 |
| lexiflux/ebook/page\_splitter.py       |       37 |       24 |     35% |17-19, 23-29, 42-54, 62-78, 82-92 |
| lexiflux/forms.py                      |       21 |       21 |      0% |      3-33 |
| lexiflux/language/google\_languages.py |       12 |        0 |    100% |           |
| lexiflux/language/translation.py       |       45 |       20 |     56% |21-25, 30, 36-38, 46-47, 69-78 |
| lexiflux/llm.py                        |      125 |      125 |      0% |     3-334 |
| lexiflux/models.py                     |      163 |       66 |     60% |37-39, 56, 66, 98, 103, 108, 112-131, 134-142, 146, 157, 172, 177-182, 185-190, 194, 200-203, 220-228, 231-232, 256, 286-309 |
| lexiflux/settings.py                   |        0 |        0 |    100% |           |
| lexiflux/signals.py                    |       16 |        5 |     69% | 40-44, 61 |
| lexiflux/tests.py                      |        0 |        0 |    100% |           |
| lexiflux/urls.py                       |        3 |        3 |      0% |       3-7 |
| lexiflux/utils.py                      |        8 |        0 |    100% |           |
| lexiflux/views.py                      |      222 |      170 |     23% |25-44, 49, 54, 63-89, 106-127, 141-157, 176-214, 220-228, 246-251, 266-312, 318-319, 326-345, 351-385, 392-417, 423-433 |
|                              **TOTAL** | **1001** |  **606** | **39%** |           |


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