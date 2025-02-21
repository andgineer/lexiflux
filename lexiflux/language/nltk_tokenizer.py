"""NTLK tokenizer utilities for language processing."""

import logging
import os
from typing import Optional

import nltk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_nltk_data(resource: str, package: Optional[str] = None) -> None:
    """Ensure NLTK data is available, downloading it if necessary.

    Args:
    resource (str): The NLTK resource to check/download (e.g., "tokenizers/punkt")
    package (str): The package name to download if different from resource (e.g., "punkt")

    """
    # Set NLTK data path to a writable directory
    if "GITHUB_WORKSPACE" in os.environ:
        nltk_data_dir = os.path.join(os.environ["GITHUB_WORKSPACE"], "nltk_data")
    else:
        nltk_data_dir = os.path.join(os.path.expanduser("~"), "nltk_data")
    os.makedirs(nltk_data_dir, exist_ok=True)
    nltk.data.path.append(nltk_data_dir)

    try:
        nltk.data.find(resource)
    except LookupError:
        try:
            nltk.download(
                package or resource.split("/")[-1],
                quiet=True,
                download_dir=nltk_data_dir,
            )
            logger.info(f"Downloaded NLTK data: {package or resource}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to download NLTK data ({resource}): {e}")
            logger.warning(f"NLTK {resource} may not be available.")


def get_punkt_tokenizer(lang_code: str) -> nltk.tokenize.punkt.PunktSentenceTokenizer:
    """Get the appropriate PunktSentenceTokenizer for the given language code.

    Args:
    lang_code (str): Language code (e.g., 'en' for English)

    Returns:
    nltk.tokenize.punkt.PunktSentenceTokenizer: The appropriate tokenizer

    """
    ensure_nltk_data(f"tokenizers/punkt/{lang_code}.pickle", "punkt")
    try:
        return nltk.data.load(f"tokenizers/punkt/{lang_code}.pickle")
    except LookupError:
        logger.warning(f"NLTK punkt tokenizer not available for {lang_code}. Using default.")
        return nltk.tokenize.punkt.PunktSentenceTokenizer()
