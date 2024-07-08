# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                     |    Stmts |     Miss |   Cover |   Missing |
|----------------------------------------- | -------: | -------: | ------: | --------: |
| lexiflux/admin.py                        |        6 |        0 |    100% |           |
| lexiflux/api.py                          |       24 |       13 |     46% | 13, 29-43 |
| lexiflux/apps.py                         |       14 |        3 |     79% |     23-28 |
| lexiflux/ebook/book\_base.py             |       71 |       47 |     34% |35-36, 43, 50, 57-91, 95-105, 110-137 |
| lexiflux/ebook/book\_epub.py             |       92 |       73 |     21% |28-40, 49-61, 68-88, 94, 103-118, 125-133, 141-147, 158-178 |
| lexiflux/ebook/book\_plain\_text.py      |      111 |       80 |     28% |39-46, 55-60, 64-75, 79-99, 104-107, 112-114, 121-145, 149-159, 166-188 |
| lexiflux/ebook/headings.py               |       36 |       28 |     22% |19-31, 37-116, 133-136 |
| lexiflux/ebook/page\_splitter.py         |       37 |       24 |     35% |17-19, 23-29, 42-54, 62-78, 82-92 |
| lexiflux/forms.py                        |       33 |       18 |     45% |14-18, 35-51 |
| lexiflux/language/sentence\_extractor.py |       51 |       36 |     29% |35-39, 50-63, 86-110 |
| lexiflux/language/translation.py         |       44 |       28 |     36% |21-25, 30, 36-37, 42-55, 68-77 |
| lexiflux/language/word\_extractor.py     |       75 |       62 |     17% |14-19, 22-28, 31-39, 42-44, 47-53, 60-109, 114-116 |
| lexiflux/lexical\_articles.py            |       10 |       10 |      0% |      3-32 |
| lexiflux/llm.py                          |      146 |      138 |      5% |    12-411 |
| lexiflux/models.py                       |      201 |       93 |     54% |49-51, 70, 80, 112, 117, 122, 126-145, 148-156, 160, 171, 192, 199-200, 204-213, 218-221, 225-227, 233-251, 268-276, 279-280, 318-350, 355-361, 365, 395-418 |
| lexiflux/settings.py                     |        0 |        0 |    100% |           |
| lexiflux/signals.py                      |       21 |       11 |     48% |     37-57 |
| lexiflux/tests.py                        |        0 |        0 |    100% |           |
| lexiflux/urls.py                         |        6 |        6 |      0% |      3-10 |
| lexiflux/utils.py                        |        8 |        5 |     38% |     10-16 |
| lexiflux/views.py                        |      344 |      321 |      7% |    28-660 |
|                                **TOTAL** | **1330** |  **996** | **25%** |           |


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