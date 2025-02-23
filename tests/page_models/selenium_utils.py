from functools import wraps
from selenium.common.exceptions import StaleElementReferenceException
import time


def retry_on_stale_element(max_attempts=3, delay=0.5):
    """
    Decorator that retries a function when StaleElementReferenceException occurs.

    Args:
        max_attempts (int): Maximum number of retry attempts
        delay (float): Delay in seconds between retries
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
            return None

        return wrapper

    return decorator
