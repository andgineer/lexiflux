from lexiflux.ebook.book_processor import BookProcessor


def test_word_num(sentence_6_words):
    splitter = BookProcessor()
    assert splitter.get_word_num(sentence_6_words, len(sentence_6_words)) == 6
