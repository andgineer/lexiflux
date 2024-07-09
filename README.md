# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------ | -------: | -------: | ------: | --------: |
| lexiflux/admin.py                               |        6 |        0 |    100% |           |
| lexiflux/api.py                                 |       24 |        7 |     71% |     32-39 |
| lexiflux/apps.py                                |       14 |        3 |     79% |     23-28 |
| lexiflux/ebook/book\_base.py                    |       71 |       31 |     56% |35-36, 43, 50, 57-91, 95-105, 130-131 |
| lexiflux/ebook/book\_epub.py                    |       92 |       35 |     62% |28-40, 49-61, 68-88, 94, 111, 114-116, 170, 176-178 |
| lexiflux/ebook/book\_plain\_text.py             |      111 |       75 |     32% |43-46, 55-60, 66-75, 79-99, 104-107, 112-114, 121-145, 149-159, 166-188 |
| lexiflux/ebook/headings.py                      |       36 |       24 |     33% |19-31, 37-116 |
| lexiflux/ebook/page\_splitter.py                |       37 |       24 |     35% |17-19, 23-29, 42-54, 62-78, 82-92 |
| lexiflux/forms.py                               |       33 |       18 |     45% |14-18, 35-51 |
| lexiflux/language/detect\_language\_fasttext.py |       29 |        7 |     76% |     52-65 |
| lexiflux/language/sentence\_extractor.py        |       25 |        2 |     92% |    41, 46 |
| lexiflux/language/translation.py                |       44 |       19 |     57% |21-25, 30, 36-37, 45-46, 68-77 |
| lexiflux/language/word\_extractor.py            |       75 |        0 |    100% |           |
| lexiflux/lexical\_articles.py                   |       10 |       10 |      0% |      3-32 |
| lexiflux/llm.py                                 |      146 |      105 |     28% |58, 68-70, 77-82, 89-107, 114-121, 128-136, 155-159, 163, 167, 181-198, 207, 212-221, 224-329, 345-379, 382, 392-411 |
| lexiflux/models.py                              |      207 |       97 |     53% |49-51, 70, 80, 112, 117, 122, 126-145, 148-156, 160, 171, 194, 198-199, 206-207, 211-220, 225-229, 233-235, 244-263, 280-288, 291-292, 330-362, 367-373, 377, 407-430 |
| lexiflux/settings.py                            |        0 |        0 |    100% |           |
| lexiflux/signals.py                             |       21 |       11 |     48% |     37-57 |
| lexiflux/tests.py                               |        0 |        0 |    100% |           |
| lexiflux/urls.py                                |        6 |        6 |      0% |      3-10 |
| lexiflux/utils.py                               |        8 |        0 |    100% |           |
| lexiflux/views.py                               |      355 |      271 |     24% |63-90, 95-114, 119, 124, 133-159, 176-197, 211-227, 247-305, 311-348, 355-381, 388-403, 410-416, 428-466, 471-484, 493-516, 523-537, 543-545, 558-562, 569-588, 594-628, 635-660, 666-676 |
|                                       **TOTAL** | **1350** |  **745** | **45%** |           |


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