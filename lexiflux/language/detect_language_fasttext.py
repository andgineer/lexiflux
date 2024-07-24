"""Detect language using fastText language identification model."""

from functools import lru_cache
from pathlib import Path
import os
import fasttext
import requests

FASTTEXT_MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"


class FastTextDetectLanguage:
    """Detect language using fastText language identification model."""

    def __init__(self) -> None:
        """Initialize."""
        self.model = self.load_model()

    def detect(self, text: str) -> str:
        """Detect language using fastText language identification model."""
        predictions = self.model.predict(text.replace("\n", ""), k=1)  # get top 1 prediction
        language = predictions[0][0].replace("__label__", "")
        # confidence = predictions[1][0]
        return language  # type: ignore

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

        return fasttext.load_model(str(fasttext_model_path))


@lru_cache(maxsize=1)
def language_detector() -> FastTextDetectLanguage:
    """Singleton for FastTextDetectLanguage."""
    return FastTextDetectLanguage()


if __name__ == "__main__":  # pragma: no cover
    print(language_detector().detect("Dobar dan!"))
