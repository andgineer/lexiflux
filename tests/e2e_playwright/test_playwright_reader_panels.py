from unittest.mock import patch

import pytest
from django.template.loader import render_to_string
from playwright.sync_api import expect

from lexiflux.language.llm import ArticleError, ArticleEvent
from tests.e2e_playwright.fakes import DroppedConnection, busy, cut_off
from tests.e2e_playwright.pages import ReaderPage

pytestmark = pytest.mark.django_db(transaction=True)

SPINNER = ".lexical-status .spinner-border"
LEFT_BLANK_LINE_PX = 4


def test_article_text_appears_progressively(reader: ReaderPage, fake_stream):
    before_first, before_done = fake_stream.gate(), fake_stream.gate()
    fake_stream.scripts["page"] = [before_first, "Once upon", before_done, " a time"]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")
    expect(panel.locator(SPINNER)).to_be_visible()

    before_first.set()
    expect(panel).to_have_text("Once upon")
    expect(panel.locator(SPINNER)).to_have_count(0)
    assert fake_stream.finished == []

    before_done.set()
    expect(panel).to_have_text("Once upon a time")
    assert fake_stream.finished == ["page"]
    assert fake_stream.requests[0].model == "pool"


def test_new_selection_aborts_the_streaming_panel(reader: ReaderPage, fake_stream):
    fake_stream.scripts["Content"] = ["alpha early", *[0.1, " alpha late"] * 100]
    fake_stream.scripts["page"] = ["beta article"]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("Content")
    expect(panel).to_contain_text("alpha early")
    reader.click_word("page")

    expect(panel).to_have_text("beta article")
    assert fake_stream.closed == ["Content"]
    assert fake_stream.finished == ["page"]
    reader.page.wait_for_timeout(500)
    expect(panel).to_have_text("beta article")


def test_replace_resets_the_text(reader: ReaderPage, fake_stream):
    gate = fake_stream.gate()
    fake_stream.scripts["page"] = ["draft answer", gate, ArticleEvent.replace("final answer")]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")
    expect(panel).to_have_text("draft answer")
    gate.set()
    expect(panel).to_have_text("final answer")


def test_cut_off_error_is_appended_after_the_text(reader: ReaderPage, fake_stream):
    fake_stream.scripts["page"] = ["partial text", cut_off]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")

    alert = panel.locator(".alert")
    expect(alert).to_contain_text("The answer was cut off")
    expect(panel).to_contain_text("partial text")
    assert panel.evaluate("el => el.lastElementChild.classList.contains('alert')")
    assert panel.evaluate("el => el.firstChild.nodeType === Node.TEXT_NODE")


def test_other_error_replaces_the_panel(reader: ReaderPage, fake_stream):
    fake_stream.scripts["page"] = ["partial text", busy]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")

    expect(panel.locator(".alert.alert-info")).to_contain_text("busy right now")
    expect(panel).not_to_contain_text("partial text")


def test_stream_ending_without_done_gets_the_cut_off_notice(reader: ReaderPage, fake_stream):
    fake_stream.scripts["page"] = ["partial text", DroppedConnection("connection dropped")]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")

    expect(panel.locator(".alert")).to_contain_text("The answer was cut off")
    expect(panel).to_contain_text("partial text")


def test_markdown_emphasis_and_line_breaks_render(reader: ReaderPage, fake_stream):
    fake_stream.scripts["page"] = ["**bold** and *italic*\n", "second line"]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")

    expect(panel.locator("b")).to_have_text("bold")
    expect(panel.locator("i")).to_have_text("italic")
    expect(panel).to_have_css("white-space", "pre-line")
    second_line_top, bold_bottom = panel.evaluate(
        """el => {
            const node = [...el.childNodes].find(n => n.textContent.includes('second line'));
            const range = document.createRange();
            range.setStart(node, node.textContent.indexOf('second line'));
            range.setEnd(node, node.textContent.length);
            return [range.getBoundingClientRect().top, el.querySelector('b').getBoundingClientRect().bottom];
        }"""
    )
    assert second_line_top >= bold_bottom


MIN_TABLE_CELL_GAP_PX = 4


def test_article_table_cells_have_a_gap(reader: ReaderPage, fake_stream):
    fake_stream.scripts["page"] = [
        "<table>\n<tr><td>mi pričamo</td><td>мы говорим</td></tr>\n",
        "<tr><td>oni pričaju</td><td>они говорят</td></tr>\n</table>",
    ]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")
    expect(panel.locator("tr")).to_have_count(2)

    gaps = panel.evaluate(
        """el => [...el.querySelectorAll('tr')].map(row => {
            const [form, translation] = row.querySelectorAll('td');
            const range = document.createRange();
            range.selectNodeContents(form);
            return translation.getBoundingClientRect().left - range.getBoundingClientRect().right;
        })"""
    )
    assert all(gap >= MIN_TABLE_CELL_GAP_PX for gap in gaps), gaps


def _alert_geometry(panel):
    return panel.evaluate(
        """el => {
            const alert = el.querySelector('.alert');
            const style = getComputedStyle(alert);
            const inner = alert.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
            const content = [...alert.children].reduce((sum, child) => {
                const s = getComputedStyle(child);
                return sum + child.offsetHeight + parseFloat(s.marginTop) + parseFloat(s.marginBottom);
            }, 0);
            const previous = alert.previousSibling;
            let textBottom = null;
            if (previous) {
                const range = document.createRange();
                range.selectNodeContents(previous);
                textBottom = range.getBoundingClientRect().bottom;
            }
            return {
                whiteSpace: style.whiteSpace,
                blankInside: inner - content,
                alertTop: alert.getBoundingClientRect().top,
                marginTop: parseFloat(style.marginTop),
                panelTop: el.getBoundingClientRect().top + parseFloat(getComputedStyle(el).paddingTop),
                textBottom,
            };
        }"""
    )


def test_error_alert_has_no_blank_gaps(reader: ReaderPage, fake_stream):
    fake_stream.scripts["page"] = [busy]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")
    expect(panel.locator(".alert")).to_be_visible()

    geometry = _alert_geometry(panel)
    assert geometry["whiteSpace"] == "normal"
    assert abs(geometry["blankInside"]) < LEFT_BLANK_LINE_PX, geometry
    assert geometry["alertTop"] - geometry["panelTop"] < LEFT_BLANK_LINE_PX, geometry


def test_cut_off_alert_follows_the_text_without_a_blank_line(reader: ReaderPage, fake_stream):
    fake_stream.scripts["page"] = ["partial text", cut_off]
    reader.open_sidebar()
    panel = reader.panel(1)

    reader.click_word("page")
    expect(panel.locator(".alert")).to_be_visible()

    geometry = _alert_geometry(panel)
    assert abs(geometry["blankInside"]) < LEFT_BLANK_LINE_PX, geometry
    gap = geometry["alertTop"] - geometry["textBottom"] - geometry["marginTop"]
    assert gap < LEFT_BLANK_LINE_PX, geometry


def test_stream_response_is_not_compressed(reader: ReaderPage, fake_stream):
    reader.open_sidebar()

    with reader.page.expect_response(lambda r: "/translate/stream" in r.url) as response_info:
        reader.click_word("page")
    response = response_info.value

    assert "gzip" in response.request.all_headers().get("accept-encoding", "")
    headers = response.all_headers()
    assert "content-encoding" not in headers
    assert headers["content-type"] == "application/x-ndjson"
    expect(reader.panel(1)).to_have_text("Article about page")


def test_inline_popup_shows_the_translation(reader: ReaderPage):
    reader.click_word("page")

    expect(reader.inline_translation()).to_have_text("Translation of page")


def test_inline_popup_shows_an_ai_error_as_an_alert(
    logged_in_page, server_url, book, language_preferences
):
    language_preferences.inline_translation_type = "Translate"
    language_preferences.inline_translation_parameters = {"model": "gpt"}
    language_preferences.save()
    error_html = render_to_string("llm-error.html", {"kind": ArticleError.BUSY}).strip()
    with patch(
        "lexiflux.views.lexical_views.generate_article",
        side_effect=ArticleError(ArticleError.BUSY, error_html),
    ):
        reader = ReaderPage(logged_in_page, server_url).open(book.code)
        reader.click_word("page")

        alert = reader.inline_translation().locator(".alert.alert-info")
        expect(alert).to_have_text("The AI models are busy right now. Please retry.")
        expect(reader.inline_translation()).not_to_contain_text("<div")
