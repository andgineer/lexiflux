import json
import urllib.parse
from pathlib import Path

import httpx

# kaikki.org pages recorded on 2026-09-25/26, trimmed to the fields the lookup reads and to the
# Russian, German and Serbo-Croatian translations ("spring" also keeps its Norwegian, Tagalog and
# Kurmanji ones, "king" its Mandarin ones). A page not listed answers 404, as there.
PAGES_FILE = Path(__file__).parent / "resources" / "wiktionary" / "kaikki_pages.jsonl"


class Kaikki:
    """kaikki.org serving the recorded pages; `fail` makes the matching pages fail."""

    def __init__(self) -> None:
        self.pages = {
            page["url"]: "\n".join(
                json.dumps(record, ensure_ascii=False) for record in page["records"]
            )
            for page in map(json.loads, PAGES_FILE.read_text(encoding="utf-8").splitlines())
        }
        self.requests: list[str] = []
        self.failures: dict[str, int | Exception] = {}

    def fail(self, url_part: str, failure: int | Exception) -> None:
        self.failures[url_part] = failure

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        for url_part, failure in self.failures.items():
            if url_part in url:
                if isinstance(failure, Exception):
                    raise failure
                return httpx.Response(failure, text="failure")
        if url in self.pages:
            return httpx.Response(200, text=self.pages[url])
        return httpx.Response(404, text="Not Found")

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handle))

    def requested(self) -> list[str]:
        """The requested pages as `<edition>/<Language>/<word>`, in request order."""
        paths = []
        for url in self.requests:
            path = urllib.parse.unquote(url.removeprefix("https://kaikki.org/"))
            edition, language, _meaning, _first, _two, name = path.split("/")
            paths.append(f"{edition}/{language}/{name.removesuffix('.jsonl')}")
        return paths
