# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| lexiflux/\_\_about\_\_.py                             |        1 |        0 |    100% |           |
| lexiflux/admin.py                                     |        6 |        0 |    100% |           |
| lexiflux/anki/anki\_common.py                         |       12 |        0 |    100% |           |
| lexiflux/anki/anki\_connect.py                        |       64 |       20 |     69% |44-46, 84-96, 98, 102-107 |
| lexiflux/anki/anki\_file.py                           |       26 |        0 |    100% |           |
| lexiflux/anki/csv\_file.py                            |       20 |        0 |    100% |           |
| lexiflux/api.py                                       |       24 |        3 |     88% |     37-39 |
| lexiflux/apps.py                                      |       13 |        0 |    100% |           |
| lexiflux/asgi.py                                      |        4 |        4 |      0% |      9-15 |
| lexiflux/backends.py                                  |       15 |        2 |     87% |     27-28 |
| lexiflux/decorators.py                                |       18 |        4 |     78% | 15, 26-28 |
| lexiflux/ebook/book\_loader\_base.py                  |      105 |        9 |     91% |58, 77, 84-85, 109-110, 146, 153, 194 |
| lexiflux/ebook/book\_loader\_epub.py                  |      177 |       10 |     94% |54, 129-133, 235, 238-240, 326-328 |
| lexiflux/ebook/book\_loader\_html.py                  |        3 |        0 |    100% |           |
| lexiflux/ebook/book\_loader\_plain\_text.py           |      114 |        9 |     92% |48-49, 104-108, 130, 177 |
| lexiflux/ebook/headings.py                            |       36 |        0 |    100% |           |
| lexiflux/ebook/html\_page\_splitter.py                |      108 |        5 |     95% |18-19, 23-24, 58 |
| lexiflux/ebook/page\_splitter.py                      |       37 |        5 |     86% |     23-29 |
| lexiflux/forms.py                                     |       12 |        0 |    100% |           |
| lexiflux/language/detect\_language\_detectlanguage.py |       25 |        4 |     84% |29-31, 33-37 |
| lexiflux/language/detect\_language\_fasttext.py       |       29 |        1 |     97% |        34 |
| lexiflux/language/google\_languages.py                |       40 |        1 |     98% |        78 |
| lexiflux/language/llm.py                              |      185 |       86 |     54% |44-47, 61-64, 69-74, 79-81, 86-88, 101-106, 113, 137, 192-197, 209-228, 264-277, 369-378, 385-436 |
| lexiflux/language/nltk\_tokenizer.py                  |       29 |        5 |     83% |25, 37-39, 55 |
| lexiflux/language/parse\_html\_text\_content.py       |      102 |        1 |     99% |       158 |
| lexiflux/language/sentence\_extractor.py              |       32 |        2 |     94% |    61, 77 |
| lexiflux/language/sentence\_extractor\_llm.py         |       52 |       39 |     25% |17, 48-92, 97-128, 133-169 |
| lexiflux/language/translation.py                      |       22 |        1 |     95% |        32 |
| lexiflux/language/word\_extractor.py                  |       85 |        8 |     91% |42-49, 53, 66 |
| lexiflux/language\_preferences\_default.py            |       16 |        2 |     88% |     46-47 |
| lexiflux/lexiflux\_settings.py                        |       51 |       14 |     73% |23-30, 35-39, 60-66, 88-89, 104 |
| lexiflux/middleware.py                                |       13 |        2 |     85% |     21-25 |
| lexiflux/models.py                                    |      448 |       42 |     91% |103, 135, 166, 182-183, 245, 251, 262, 284, 318-321, 336, 387, 426, 428, 437-442, 496-498, 501, 508, 532, 534-535, 537-538, 541, 585, 699, 709, 733, 811, 822, 848, 885 |
| lexiflux/settings.py                                  |       37 |        4 |     89% |   192-196 |
| lexiflux/signals.py                                   |       14 |       14 |      0% |      3-24 |
| lexiflux/tests.py                                     |        0 |        0 |    100% |           |
| lexiflux/urls.py                                      |       15 |        2 |     87% |   105-107 |
| lexiflux/utils.py                                     |       25 |       11 |     56% |     29-40 |
| lexiflux/views/ai\_settings\_views.py                 |       41 |        4 |     90% |69-70, 73, 80 |
| lexiflux/views/auth\_views.py                         |       32 |        3 |     91% | 43, 49-50 |
| lexiflux/views/language\_preferences\_views.py        |      198 |       37 |     81% |143-145, 168-169, 181, 247, 256-259, 270-279, 291, 309-314, 327, 335, 340, 348-352, 363, 372-376 |
| lexiflux/views/lexical\_views.py                      |       81 |       25 |     69% |48, 65, 84-117, 144, 178-200 |
| lexiflux/views/library\_views.py                      |      118 |       10 |     92% |61-62, 106-110, 187-188, 204-205, 217 |
| lexiflux/views/reader\_views.py                       |      275 |       37 |     87% |69-71, 117, 137, 208, 212, 217-219, 264, 289, 293, 308, 312, 325, 329, 341, 345, 373, 397, 401, 435-438, 443, 497, 506, 512-519 |
| lexiflux/views/words\_export.py                       |      143 |       28 |     80% |66-71, 106-111, 146, 170-178, 191, 240, 271, 294-300 |
| lexiflux/wsgi.py                                      |        4 |        4 |      0% |      9-15 |
|                                             **TOTAL** | **2907** |  **458** | **84%** |           |


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