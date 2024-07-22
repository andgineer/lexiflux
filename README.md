# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------ | -------: | -------: | ------: | --------: |
| lexiflux/admin.py                               |        6 |        0 |    100% |           |
| lexiflux/api.py                                 |       24 |        3 |     88% |     37-39 |
| lexiflux/apps.py                                |       14 |        0 |    100% |           |
| lexiflux/ebook/book\_base.py                    |       73 |        5 |     93% |54, 61, 102, 141-142 |
| lexiflux/ebook/book\_epub.py                    |       92 |        8 |     91% |94, 111, 114-116, 176-178 |
| lexiflux/ebook/book\_html.py                    |        3 |        3 |      0% |       3-9 |
| lexiflux/ebook/book\_plain\_text.py             |      114 |        7 |     94% |61-62, 116-118, 139, 186 |
| lexiflux/ebook/headings.py                      |       36 |        0 |    100% |           |
| lexiflux/ebook/page\_splitter.py                |       37 |        5 |     86% |     23-29 |
| lexiflux/forms.py                               |       33 |       18 |     45% |14-18, 35-51 |
| lexiflux/language/detect\_language\_fasttext.py |       21 |        0 |    100% |           |
| lexiflux/language/google\_languages.py          |       12 |        0 |    100% |           |
| lexiflux/language/html\_tags\_cleaner.py        |      101 |        1 |     99% |       156 |
| lexiflux/language/llm.py                        |      165 |      102 |     38% |35-38, 43-48, 63-65, 70-72, 85-90, 97, 121, 182-187, 199-219, 254-267, 295-336, 348, 351-395, 398 |
| lexiflux/language/sentence\_extractor.py        |       28 |        5 |     82% |10-13, 52, 63, 79 |
| lexiflux/language/sentence\_extractor\_llm.py   |       52 |       39 |     25% |17, 48-92, 97-128, 133-167 |
| lexiflux/language/translation.py                |       44 |        0 |    100% |           |
| lexiflux/language/word\_extractor.py            |       64 |        4 |     94% |16-17, 44, 51 |
| lexiflux/models.py                              |      232 |       42 |     82% |88, 98, 137, 146-147, 164, 175, 197, 231-234, 249, 270-278, 281-288, 310, 312-313, 315-316, 319, 360, 401-412, 467-479 |
| lexiflux/settings.py                            |        0 |        0 |    100% |           |
| lexiflux/signals.py                             |       20 |        2 |     90% |     45-46 |
| lexiflux/tests.py                               |        0 |        0 |    100% |           |
| lexiflux/urls.py                                |        9 |        0 |    100% |           |
| lexiflux/utils.py                               |        8 |        0 |    100% |           |
| lexiflux/views/auth\_views.py                   |       31 |        3 |     90% | 43, 50-55 |
| lexiflux/views/language\_preferences\_ajax.py   |      154 |       94 |     39% |95-97, 104-119, 126-149, 161-199, 204-222, 231-259, 266-280 |
| lexiflux/views/lexical\_views.py                |       71 |       31 |     56% |41-52, 65, 81-119, 167-183 |
| lexiflux/views/library\_views.py                |       30 |        2 |     93% |     45-46 |
| lexiflux/views/reader\_views.py                 |      107 |        5 |     95% |45, 64, 76, 162, 195 |
|                                       **TOTAL** | **1581** |  **379** | **76%** |           |


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