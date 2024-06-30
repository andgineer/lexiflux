# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                   |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------- | -------: | -------: | ------: | --------: |
| lexiflux/api.py                        |       24 |        3 |     88% |     37-39 |
| lexiflux/apps.py                       |       14 |        0 |    100% |           |
| lexiflux/ebook/book\_base.py           |       72 |        5 |     93% |44, 51, 92, 131-132 |
| lexiflux/ebook/book\_epub.py           |       92 |       11 |     88% |85-87, 94, 111, 114-116, 176-178 |
| lexiflux/ebook/book\_plain\_text.py    |      111 |        7 |     94% |58-59, 112-114, 135, 182 |
| lexiflux/ebook/headings.py             |       36 |        0 |    100% |           |
| lexiflux/ebook/page\_splitter.py       |       37 |        5 |     86% |     23-29 |
| lexiflux/language/google\_languages.py |       12 |        0 |    100% |           |
| lexiflux/language/translation.py       |       45 |        9 |     80% |21-25, 30, 36-38 |
| lexiflux/llm.py                        |      125 |      125 |      0% |     3-333 |
| lexiflux/models.py                     |      132 |       23 |     83% |41, 83, 88, 93, 104, 113-114, 120-122, 131, 142, 170, 174, 229-252 |
| lexiflux/settings.py                   |        0 |        0 |    100% |           |
| lexiflux/signals.py                    |       13 |        0 |    100% |           |
| lexiflux/tests.py                      |        0 |        0 |    100% |           |
| lexiflux/urls.py                       |        3 |        0 |    100% |           |
| lexiflux/utils.py                      |        8 |        0 |    100% |           |
| lexiflux/views.py                      |      151 |       78 |     48% |24-42, 47, 52, 66, 70-87, 104-125, 142-144, 148-155, 190-206, 220-254, 269-270, 274-286, 292-302 |
|                              **TOTAL** |  **875** |  **266** | **70%** |           |


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