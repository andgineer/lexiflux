# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| lexiflux/admin.py                                     |        6 |        0 |    100% |           |
| lexiflux/api.py                                       |       24 |        7 |     71% |     32-39 |
| lexiflux/apps.py                                      |        7 |        0 |    100% |           |
| lexiflux/decorators.py                                |       18 |        4 |     78% | 15, 26-28 |
| lexiflux/ebook/book\_base.py                          |       73 |        5 |     93% |55, 62, 103, 142-143 |
| lexiflux/ebook/book\_epub.py                          |       95 |        8 |     92% |100, 117, 120-122, 182-184 |
| lexiflux/ebook/book\_html.py                          |        3 |        0 |    100% |           |
| lexiflux/ebook/book\_plain\_text.py                   |      118 |        9 |     92% |61-62, 117-121, 143, 190 |
| lexiflux/ebook/headings.py                            |       36 |        0 |    100% |           |
| lexiflux/ebook/page\_splitter.py                      |       37 |        5 |     86% |     23-29 |
| lexiflux/forms.py                                     |       33 |       18 |     45% |14-18, 35-51 |
| lexiflux/language/detect\_language\_detectlanguage.py |       25 |        4 |     84% |29-31, 33-37 |
| lexiflux/language/detect\_language\_fasttext.py       |       29 |        1 |     97% |        34 |
| lexiflux/language/google\_languages.py                |       17 |        0 |    100% |           |
| lexiflux/language/llm.py                              |      180 |      106 |     41% |50-53, 58-63, 78-80, 85-87, 100-105, 112, 136, 198-203, 215-234, 270-283, 311-352, 359-371, 378-427 |
| lexiflux/language/nltk\_tokenizer.py                  |       29 |        5 |     83% |25, 37-39, 55 |
| lexiflux/language/parse\_html\_text\_content.py       |      102 |        1 |     99% |       157 |
| lexiflux/language/sentence\_extractor.py              |       20 |        2 |     90% |    45, 61 |
| lexiflux/language/sentence\_extractor\_llm.py         |       52 |       39 |     25% |17, 48-92, 97-128, 133-167 |
| lexiflux/language/translation.py                      |       22 |        8 |     64% |31-38, 48, 53, 63 |
| lexiflux/language/word\_extractor.py                  |       85 |        8 |     91% |42-49, 53, 66 |
| lexiflux/lexiflux\_settings.py                        |       37 |        9 |     76% |16-23, 28-32, 68, 81 |
| lexiflux/middleware.py                                |       13 |        2 |     85% |     21-25 |
| lexiflux/models.py                                    |      252 |       54 |     79% |121, 149, 160, 169-170, 198, 220, 254-257, 272, 293-301, 304-311, 331, 351-362, 365-366, 420, 445-460, 465, 472, 513-525 |
| lexiflux/signals.py                                   |       23 |       23 |      0% |      3-69 |
| lexiflux/tests.py                                     |        0 |        0 |    100% |           |
| lexiflux/urls.py                                      |       10 |        0 |    100% |           |
| lexiflux/utils.py                                     |        8 |        0 |    100% |           |
| lexiflux/views/ai\_settings\_views.py                 |       34 |       22 |     35% | 23, 30-68 |
| lexiflux/views/auth\_views.py                         |       32 |        3 |     91% | 43, 49-50 |
| lexiflux/views/language\_preferences\_ajax.py         |      171 |      116 |     32% |51, 81-101, 108-139, 146-163, 173-194, 201-221, 233-273, 281-299, 309-337, 345-361 |
| lexiflux/views/lexical\_views.py                      |       75 |       50 |     33% |41-52, 57, 70-129, 140-199 |
| lexiflux/views/library\_views.py                      |      114 |       56 |     51% |59-60, 77-121, 141-142, 171-174, 180-191, 197-217 |
| lexiflux/views/reader\_views.py                       |      107 |        9 |     92% |45, 64, 95-100, 164, 197 |
|                                             **TOTAL** | **1887** |  **574** | **70%** |           |


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