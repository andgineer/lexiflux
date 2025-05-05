"""Profile the HTML page splitter for performance analysis."""

import time
import cProfile
import pstats
from io import StringIO

from lexiflux.ebook.html_page_splitter import HtmlPageSplitter


def profile_splitting(html_content, target_size=3000):
    """Profile the HTML page splitting process."""
    start_time = time.time()

    # Parse full document with lxml (for comparison)
    parse_start = time.time()
    from lxml import etree

    tree = etree.HTML(html_content)
    parse_time = time.time() - parse_start

    # Profile the splitting
    pr = cProfile.Profile()
    pr.enable()

    splitter = HtmlPageSplitter(content=html_content, target_page_size=target_size)
    pages_list = list(splitter.pages())

    pr.disable()

    # Get profiling results
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)  # Print top 20 time-consuming functions

    total_time = time.time() - start_time

    print(f"Parsing time: {parse_time:.4f} seconds")
    print(f"Total splitting time: {total_time:.4f} seconds")
    print(f"Number of pages: {len(pages_list)}")
    print("\nProfiling results:")
    print(s.getvalue())

    return pages_list


if __name__ == "__main__":
    test_html = """
    <html>
    <body>
    <h1>Test Document</h1>
    """

    for i in range(1000):
        test_html += f"<p>Paragraph {i} with some content. This is a test paragraph with multiple sentences. "
        test_html += (
            f"This is sentence 2 of paragraph {i}. And here's another one to make it longer.</p>\n"
        )

    test_html += """
    </body>
    </html>
    """

    print(f"Test document size: {len(test_html)} characters")

    pages = profile_splitting(test_html, target_size=3000)

    print(f"Successfully generated {len(pages)} pages")
