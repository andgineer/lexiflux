import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from llmbroker import LLMTimeoutError, StreamInterruptedError

from lexiflux.language.llm import ArticleEvent, ArticleRequest, article_error

STEP_TIMEOUT_SECONDS = 10


class DroppedConnection(Exception):
    pass


Step = str | ArticleEvent | threading.Event | float | Exception | Callable[[ArticleRequest], Any]


def cut_off(req: ArticleRequest) -> ArticleEvent:
    return ArticleEvent.error(
        article_error(StreamInterruptedError("died", llm_name="fake"), req, had_text=True)
    )


def busy(req: ArticleRequest) -> ArticleEvent:
    return ArticleEvent.error(article_error(LLMTimeoutError("wait ran out"), req, had_text=False))


@dataclass
class FakeArticleStream:
    scripts: dict[str, list[Step]] = field(default_factory=dict)
    requests: list[ArticleRequest] = field(default_factory=list)
    finished: list[str] = field(default_factory=list)
    closed: list[str] = field(default_factory=list)
    gates: list[threading.Event] = field(default_factory=list)

    def gate(self) -> threading.Event:
        event = threading.Event()
        self.gates.append(event)
        return event

    def release_all(self) -> None:
        for event in self.gates:
            event.set()

    def __call__(self, req: ArticleRequest) -> Iterator[ArticleEvent]:
        self.requests.append(req)
        return self._run(req, self.scripts.get(req.word, [f"Article about {req.word}"]))

    def _run(self, req: ArticleRequest, steps: list[Step]) -> Iterator[ArticleEvent]:
        try:
            for step in steps:
                if isinstance(step, threading.Event):
                    assert step.wait(STEP_TIMEOUT_SECONDS), "the test never released a gate"
                elif isinstance(step, float):
                    time.sleep(step)
                elif isinstance(step, Exception):
                    raise step
                elif isinstance(step, str):
                    yield ArticleEvent.delta(step)
                elif isinstance(step, ArticleEvent):
                    yield step
                else:
                    yield step(req)
            self.finished.append(req.word)
        except GeneratorExit:
            self.closed.append(req.word)
            raise
