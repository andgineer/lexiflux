from lexiflux.ebook.headings import HeadingDetector


def test_get_word_num_words(sentence_6_words):
    splitter = HeadingDetector()
    assert splitter.get_word_num(sentence_6_words, len(sentence_6_words)) == 6


def test_get_word_num_no_separators():
    splitter = HeadingDetector()
    assert splitter.get_word_num("a"*10) == 1
