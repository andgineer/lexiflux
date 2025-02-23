import allure
import pytest
from lexiflux.ebook.book_loader_plain_text import (
    BookLoaderPlainText,
)  # Adjust the import according to your project structure


# Helper function to create a temporary file
def create_temp_file(content, encoding, tmpdir):
    file_path = tmpdir.join("test_file.txt")
    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)
    return file_path


@allure.epic("Book import")
@allure.feature("Encoding detection")
@pytest.mark.django_db
@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1", "utf-16"])
def test_read_file_with_various_encodings(encoding, tmpdir):
    content = "Sample text for testing."
    file_path = create_temp_file(content, encoding, tmpdir)

    book = BookLoaderPlainText(str(file_path))
    assert book.read_file(str(file_path)) == content


@allure.epic("Book import")
@allure.feature("Encoding detection")
def test_read_file_nonexistent(tmpdir):
    non_existent_file = tmpdir.join("non_existent.txt")

    with pytest.raises(FileNotFoundError):
        book = BookLoaderPlainText(str(non_existent_file))


@allure.epic("Book import")
@allure.feature("Encoding detection")
@pytest.mark.django_db
def test_read_file_undetectable_encoding(tmpdir):
    # Create a file with content that's difficult to detect encoding-wise
    # This content should be crafted in a way that challenges the chardet library
    challenging_content = "..."  # Replace with appropriate content
    file_path = create_temp_file(challenging_content, "utf-8", tmpdir)

    book = BookLoaderPlainText(str(file_path))
    # You might need to adjust the assertion based on expected behavior
    assert book.read_file(str(file_path)) == challenging_content
