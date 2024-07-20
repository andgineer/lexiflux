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
| lexiflux/language/html\_tags\_cleaner.py        |       98 |        1 |     99% |       149 |
| lexiflux/language/llm.py                        |      165 |      122 |     26% |35-38, 43-48, 53, 63-65, 70-72, 85-90, 97, 109-112, 115-117, 121, 124-126, 182-187, 199-219, 222-237, 254-267, 295-336, 348, 351-395, 398 |
| lexiflux/language/sentence\_extractor.py        |       28 |        5 |     82% |10-13, 52, 63, 79 |
| lexiflux/language/sentence\_extractor\_llm.py   |       52 |       39 |     25% |17, 48-92, 97-128, 133-167 |
| lexiflux/language/translation.py                |       43 |        0 |    100% |           |
| lexiflux/language/word\_extractor.py            |       51 |        4 |     92% |16-17, 43, 50 |
| lexiflux/models.py                              |      226 |       38 |     83% |87, 97, 136, 145-146, 163, 174, 196, 241, 262-270, 273-280, 302, 304-305, 307-308, 311, 352, 393-404, 459-471 |
| lexiflux/settings.py                            |        0 |        0 |    100% |           |
| lexiflux/signals.py                             |       20 |        2 |     90% |     45-46 |
| lexiflux/tests.py                               |        0 |        0 |    100% |           |
| lexiflux/urls.py                                |        6 |        0 |    100% |           |
| lexiflux/utils.py                               |        8 |        0 |    100% |           |
| lexiflux/views.py                               |      394 |      165 |     58% |78, 85-90, 125, 144, 156, 238, 269-280, 293, 309-347, 395-411, 462-488, 495-510, 517-540, 552-590, 595-613, 622-650, 657-671, 677-679, 692-697, 704-707, 714-733, 768-769, 795 |
|                                       **TOTAL** | **1548** |  **422** | **73%** |           |


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