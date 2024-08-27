import pytest
from django.core.exceptions import ValidationError
from lexiflux.models import Book, Author, Language


@pytest.mark.django_db
def test_generate_unique_book_code_cyrillic():
    author = Author.objects.create(name="Лев Толстой")
    language = Language.objects.get(name="Russian")
    book = Book(
        title="Война и мир",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "vojna-mir-tolstoj"


@pytest.mark.django_db
def test_generate_unique_book_code_chinese():
    author = Author.objects.create(name="老子")
    language = Language.objects.get(name="Chinese (Simplified)")
    book = Book(
        title="道德经",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "dao-de-zi"


@pytest.mark.django_db
def test_generate_unique_book_code_mixed_script():
    author = Author.objects.create(name="Haruki 村上")
    language = Language.objects.get(name="Japanese")
    book = Book(
        title="1Q84 いちきゅうはちよん",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "1q84-ichikiyuuhachiyon-shang"


@pytest.mark.django_db
def test_generate_unique_book_code_with_diacritics():
    author = Author.objects.create(name="François Rabelais")
    language = Language.objects.get(name="French")
    book = Book(
        title="Gargantua et Pantagruel",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "gargantua-pantagruel-rabelais"


@pytest.mark.django_db
def test_generate_unique_book_code_arabic():
    author = Author.objects.create(name="نجيب محفوظ")
    language = Language.objects.get(name="Arabic")
    book = Book(
        title="أولاد حارتنا",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "wld-hrtn-mhfwz"


@pytest.mark.django_db
def test_generate_unique_book_code_greek():
    author = Author.objects.create(name="Νίκος Καζαντζάκης")
    language = Language.objects.get(name="Greek")
    book = Book(
        title="Βίος και Πολιτεία του Αλέξη Ζορμπά",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "vios-kai-kazantzakis"


@pytest.mark.django_db
def test_generate_unique_book_code_long_title():
    author = Author.objects.create(name="Victor Hugo")
    language = Language.objects.get(name="French")
    book = Book(
        title="Les Misérables: A French Historical Novel by Victor Hugo, First Published in 1862, Considered One of the Greatest Novels of the 19th Century",
        author=author,
        language=language
    )
    book.save()

    assert len(book.code) <= 100
    assert book.code == "les-miserables-hugo"


@pytest.mark.django_db
def test_generate_unique_book_code_collision():
    author1 = Author.objects.create(name="John Doe")
    author2 = Author.objects.create(name="Jane Doe")
    language = Language.objects.get(name="English")

    book1 = Book(
        title="The Test Book",
        author=author1,
        language=language
    )
    book1.save()

    book2 = Book(
        title="The Test Book",
        author=author2,
        language=language
    )
    book2.save()

    assert book1.code != book2.code
    assert book1.code == "test-book-doe"
    assert book2.code == "test-book-doe-1"


@pytest.mark.django_db
def test_generate_unique_book_code_special_characters():
    author = Author.objects.create(name="A!u@t#h$o%r^")
    language = Language.objects.get(name="English")
    book = Book(
        title="S*p(e)c_i+a=l C_h/a\\r<a>c{t}e[r]s",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "special-characters-author"


@pytest.mark.django_db
def test_generate_unique_book_code_empty():
    author = Author.objects.create(name="@#$%^")
    language = Language.objects.get(name="English")
    book = Book(
        title="*()_+= _/\\<>{}[]",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "book"


@pytest.mark.django_db
def test_generate_unique_book_code_ignore_initials():
    author = Author.objects.create(name="Толстой Л.Н.")
    language = Language.objects.get(name="Russian")
    book = Book(
        title="Война и мир",
        author=author,
        language=language
    )
    book.save()

    assert book.code == "vojna-mir-tolstoj"