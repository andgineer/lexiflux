"""Detect language using fastText language identification model."""

import hashlib
import logging
from functools import lru_cache
from pathlib import Path
import os
from typing import Any

import fasttext
import requests


logger = logging.getLogger(__name__)

FASTTEXT_MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"


class FastTextDetectLanguage:
    """Detect language using fastText language identification model."""

    def __init__(self) -> None:
        """Initialize."""
        self.model = self.load_model()

    def detect(self, text: str) -> str:
        """Detect language using fastText language identification model."""
        predictions = self.model.predict(text.replace("\n", ""), k=1)  # get top 1 prediction
        return predictions[0][0].replace("__label__", "")  # type: ignore

    def detect_all(self, text: str) -> Any:
        """Return 1st 3 predictions with probabilities."""
        return self.model.predict(text.replace("\n", ""), k=3)

    def load_model(self) -> fasttext.FastText._FastText:
        """Load fastText language identification model is downloaded.

        1st check if the model is downloaded, if not download it.
        """
        if "GITHUB_WORKSPACE" in os.environ:
            fasttext_data_dir = Path(os.environ["GITHUB_WORKSPACE"]) / "fasttext_data"
        else:
            fasttext_data_dir = Path(os.path.expanduser("~")) / "fasttext_data"
        fasttext_model_path = fasttext_data_dir / "lid.176.bin"
        os.makedirs(os.path.dirname(fasttext_model_path), exist_ok=True)

        if not fasttext_model_path.exists():
            response = requests.get(FASTTEXT_MODEL_URL, stream=True, timeout=10)
            response.raise_for_status()
            with fasttext_model_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

        file_size = f"{fasttext_model_path.stat().st_size:,}"
        md5_hash = hashlib.md5(fasttext_model_path.read_bytes()).hexdigest()
        hash_groups = " ".join(md5_hash[i : i + 4] for i in range(0, 32, 4))
        logger.info(f"{fasttext_model_path}: {file_size} bytes, md5: {hash_groups}")

        model = fasttext.load_model(str(fasttext_model_path))
        labels = model.get_labels()
        if all("__label__" not in label for label in labels):
            raise ValueError(f"Model does not appear to be a language detection model: {labels}")
        return model


@lru_cache(maxsize=1)
def language_detector() -> FastTextDetectLanguage:
    """Singleton for FastTextDetectLanguage."""
    return FastTextDetectLanguage()


if __name__ == "__main__":  # pragma: no cover
    print(language_detector().detect("Dobar dan!"))
