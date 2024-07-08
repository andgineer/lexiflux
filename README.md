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
| lexiflux/language/sentence\_extractor.py |       51 |        6 |     88% |59-61, 89-90, 97 |
| lexiflux/language/translation.py         |       44 |        0 |    100% |           |
| lexiflux/language/word\_extractor.py     |       75 |        0 |    100% |           |
| lexiflux/lexical\_articles.py            |       10 |       10 |      0% |      3-32 |
| lexiflux/llm.py                          |      143 |      105 |     27% |32, 42-44, 51-56, 63-81, 88-95, 102-110, 129-133, 137, 141, 155-172, 181, 186-195, 198-303, 319-353, 356, 366-385 |
| lexiflux/models.py                       |      201 |       23 |     89% |70, 80, 133, 142-143, 160, 171, 192, 205, 235, 270, 272-273, 276, 352-353, 398-410 |
| lexiflux/settings.py                     |        0 |        0 |    100% |           |
| lexiflux/signals.py                      |       21 |        2 |     90% |     41-42 |
| lexiflux/tests.py                        |        0 |        0 |    100% |           |
| lexiflux/urls.py                         |        6 |        0 |    100% |           |
| lexiflux/utils.py                        |        8 |        0 |    100% |           |
| lexiflux/views.py                        |      344 |      128 |     63% |69, 76-81, 116, 135, 144, 213, 268-288, 338-362, 369-384, 391-397, 409-447, 452-465, 472-495, 500-514, 520-522, 535-536, 543-562, 597-598, 624 |
|                                **TOTAL** | **1339** |  **320** | **76%** |           |


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