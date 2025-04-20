import logging
import time
from contextlib import contextmanager

log = logging.getLogger()


@contextmanager
def timing(description="Operation"):
    """A simple context manager for timing code blocks."""
    start_time = time.time()
    yield
    elapsed_time = time.time() - start_time
    log.info(f"{description} completed in {elapsed_time:.3f} seconds")
