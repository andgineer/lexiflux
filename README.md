# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| lexiflux/\_\_about\_\_.py                             |        1 |        0 |    100% |           |
| lexiflux/admin.py                                     |        6 |        0 |    100% |           |
| lexiflux/api.py                                       |       24 |       24 |      0% |      3-43 |
| lexiflux/apps.py                                      |       13 |        0 |    100% |           |
| lexiflux/asgi.py                                      |        4 |        4 |      0% |      9-15 |
| lexiflux/backends.py                                  |       15 |       15 |      0% |      3-29 |
| lexiflux/decorators.py                                |       18 |        6 |     67% | 15, 25-29 |
| lexiflux/ebook/book\_loader\_base.py                  |      102 |       68 |     33% |48-49, 58, 62-93, 98-106, 110-129, 134-135, 142, 149, 156-190, 194-204 |
| lexiflux/ebook/book\_loader\_epub.py                  |       97 |       39 |     60% |25-34, 41-65, 72-98, 104, 121, 124-126, 180, 186-188 |
| lexiflux/ebook/book\_loader\_html.py                  |        3 |        3 |      0% |       3-9 |
| lexiflux/ebook/book\_loader\_plain\_text.py           |      114 |       80 |     30% |44-50, 56-65, 69-89, 93-99, 103-109, 116-140, 144-154, 161-183 |
| lexiflux/ebook/headings.py                            |       36 |       24 |     33% |19-31, 37-116 |
| lexiflux/ebook/page\_splitter.py                      |       37 |       24 |     35% |17-19, 23-29, 42-54, 62-78, 82-92 |
| lexiflux/forms.py                                     |       33 |       33 |      0% |      3-51 |
| lexiflux/language/detect\_language\_detectlanguage.py |       25 |        4 |     84% |29-31, 33-37 |
| lexiflux/language/detect\_language\_fasttext.py       |       29 |        1 |     97% |        34 |
| lexiflux/language/google\_languages.py                |       17 |        2 |     88% |    20, 25 |
| lexiflux/language/llm.py                              |      185 |      110 |     41% |41-44, 58-61, 66-71, 86-88, 93-95, 108-113, 120, 144, 206-211, 223-242, 278-291, 319-360, 367-376, 383-434 |
| lexiflux/language/nltk\_tokenizer.py                  |       29 |        5 |     83% |25, 37-39, 55 |
| lexiflux/language/parse\_html\_text\_content.py       |      102 |        1 |     99% |       157 |
| lexiflux/language/sentence\_extractor.py              |       20 |        2 |     90% |    45, 61 |
| lexiflux/language/sentence\_extractor\_llm.py         |       52 |       39 |     25% |17, 48-92, 97-128, 133-167 |
| lexiflux/language/translation.py                      |       22 |        8 |     64% |31-38, 48, 53, 63 |
| lexiflux/language/word\_extractor.py                  |       85 |       24 |     72% |42-49, 53, 66, 130-150 |
| lexiflux/language\_preferences\_default.py            |       16 |       12 |     25% |     30-58 |
| lexiflux/lexiflux\_settings.py                        |       51 |       14 |     73% |23-30, 35-39, 60-66, 88-89, 104 |
| lexiflux/middleware.py                                |       13 |        4 |     69% |     20-26 |
| lexiflux/models.py                                    |      287 |      140 |     51% |74-76, 95, 108-117, 127, 155, 159-178, 181-189, 193, 204, 226, 229-232, 243-246, 251-256, 260-263, 267-270, 276-294, 299-307, 310-317, 329, 351-359, 362-374, 377-378, 381, 403-414, 417-418, 456-458, 471-472, 480-509, 514, 521, 551-574 |
| lexiflux/settings.py                                  |       31 |        0 |    100% |           |
| lexiflux/signals.py                                   |       14 |       14 |      0% |      3-24 |
| lexiflux/tests.py                                     |        0 |        0 |    100% |           |
| lexiflux/urls.py                                      |       10 |       10 |      0% |      3-14 |
| lexiflux/utils.py                                     |        8 |        0 |    100% |           |
| lexiflux/views/reader\_views.py                       |      124 |      100 |     19% |25-34, 39-57, 62, 67, 76-117, 135-160, 174-179, 185-203, 210-235 |
| lexiflux/wsgi.py                                      |        4 |        4 |      0% |      9-15 |
|                                             **TOTAL** | **1627** |  **814** | **50%** |           |


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