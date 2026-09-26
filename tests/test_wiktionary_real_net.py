import os

import pytest

from lexiflux.language.wiktionary import lookup

pytestmark = [
    pytest.mark.real_net,
    pytest.mark.django_db,
    pytest.mark.skipif(
        os.environ.get("LEXIFLUX_REAL_NET") != "1",
        reason="fetches kaikki.org; set LEXIFLUX_REAL_NET=1",
    ),
]


@pytest.fixture
def no_real_kaikki_calls():
    # Overrides the conftest's guard: this test is the one that reaches kaikki.org.
    return


def test_kaikki_serves_be_from_both_editions():
    # A changed page layout answers 404 like a missing word, so only a known word tells them apart.
    entries = lookup("be", "en", "ru")

    senses = {entry.edition: [sense.text for sense in entry.senses] for entry in reversed(entries)}
    assert set(senses) == {"ru", "en"}
    assert entries[0].word == "be"
    assert any("быть" in sense for sense in senses["ru"])
    assert any("быть" in sense for sense in senses["en"])
