# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------ | -------: | -------: | ------: | --------: |
| lexiflux/admin.py                               |        6 |        0 |    100% |           |
| lexiflux/api.py                                 |       24 |        3 |     88% |     37-39 |
| lexiflux/apps.py                                |       14 |        0 |    100% |           |
| lexiflux/ebook/book\_base.py                    |       71 |        5 |     93% |43, 50, 91, 130-131 |
| lexiflux/ebook/book\_epub.py                    |       92 |        8 |     91% |94, 111, 114-116, 176-178 |
| lexiflux/ebook/book\_plain\_text.py             |      111 |        7 |     94% |58-59, 112-114, 135, 182 |
| lexiflux/ebook/headings.py                      |       36 |        0 |    100% |           |
| lexiflux/ebook/page\_splitter.py                |       37 |        5 |     86% |     23-29 |
| lexiflux/forms.py                               |       33 |       18 |     45% |14-18, 35-51 |
| lexiflux/language/detect\_language\_fasttext.py |       21 |        0 |    100% |           |
| lexiflux/language/google\_languages.py          |       12 |        0 |    100% |           |
| lexiflux/language/html\_tags\_cleaner.py        |       32 |        0 |    100% |           |
| lexiflux/language/llm.py                        |      154 |      113 |     27% |33-38, 43, 53-55, 60-62, 67-72, 79, 89-96, 99-101, 105, 108-110, 156, 168-184, 187-202, 219-232, 260-301, 313, 316-361, 364 |
| lexiflux/language/sentence\_extractor.py        |       28 |        5 |     82% |10-13, 52, 63, 79 |
| lexiflux/language/sentence\_extractor\_llm.py   |       52 |       39 |     25% |17, 48-92, 97-128, 133-167 |
| lexiflux/language/translation.py                |       43 |        0 |    100% |           |
| lexiflux/language/word\_extractor.py            |       75 |        0 |    100% |           |
| lexiflux/models.py                              |      222 |       36 |     84% |85, 95, 134, 143-144, 161, 172, 194, 239, 260-268, 271-278, 300, 302-303, 306, 347, 388-399, 454-466 |
| lexiflux/settings.py                            |        0 |        0 |    100% |           |
| lexiflux/signals.py                             |       20 |        2 |     90% |     45-46 |
| lexiflux/tests.py                               |        0 |        0 |    100% |           |
| lexiflux/urls.py                                |        6 |        0 |    100% |           |
| lexiflux/utils.py                               |        8 |        0 |    100% |           |
| lexiflux/views.py                               |      371 |      148 |     60% |73, 80-85, 120, 139, 151, 233, 264-275, 288, 298-316, 362-378, 429-455, 462-477, 484-502, 514-552, 557-570, 579-602, 609-623, 629-631, 644-649, 656-675, 710-711, 737 |
|                                       **TOTAL** | **1468** |  **389** | **74%** |           |


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