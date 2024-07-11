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
| lexiflux/language/llm.py                        |      168 |      126 |     25% |62-67, 74, 84-86, 93-98, 105-123, 130-137, 144-152, 162-167, 171, 196, 214-227, 253-293, 305, 310-342, 345-460, 469, 479-497 |
| lexiflux/language/sentence\_extractor.py        |       25 |        3 |     88% |47, 58, 74 |
| lexiflux/language/sentence\_extractor\_llm.py   |       52 |       39 |     25% |17, 48-92, 97-128, 133-167 |
| lexiflux/language/translation.py                |       44 |        0 |    100% |           |
| lexiflux/language/word\_extractor.py            |       75 |        0 |    100% |           |
| lexiflux/models.py                              |      224 |       33 |     85% |71, 81, 134, 143-144, 161, 172, 197, 216, 250, 272-280, 283-290, 309, 311-312, 315, 399-400, 445-457 |
| lexiflux/settings.py                            |        0 |        0 |    100% |           |
| lexiflux/signals.py                             |       21 |        2 |     90% |     41-42 |
| lexiflux/tests.py                               |        0 |        0 |    100% |           |
| lexiflux/urls.py                                |        6 |        0 |    100% |           |
| lexiflux/utils.py                               |        8 |        0 |    100% |           |
| lexiflux/views.py                               |      365 |      148 |     59% |71, 78-83, 118, 137, 149, 169-170, 231, 259-270, 281-305, 331-345, 397-423, 430-445, 452-458, 470-508, 513-526, 535-558, 565-579, 585-587, 600-604, 611-630, 665-666, 692 |
|                                       **TOTAL** | **1445** |  **397** | **73%** |           |


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