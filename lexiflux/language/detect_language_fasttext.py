"""Detect language using fastText language identification model."""

from typing import Tuple, Any, Optional
import os
import fasttext


# Path to the model file
MODEL_PATH = "lid.176.bin"


# Function to download the model if it doesn't exist
def download_model() -> None:
    """Download the fastText language identification model."""
    if not os.path.exists(MODEL_PATH):
        print("Downloading fastText language identification model...")
        os.system("wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin")
        print("Model downloaded successfully.")


# Function to load the model
def load_model() -> fasttext.FastText._FastText:
    """Load the fastText language identification model."""
    if not os.path.exists(MODEL_PATH):
        download_model()
    return fasttext.load_model(MODEL_PATH)


# Global variable to store the loaded model
MODEL: Optional[Any] = None


def detect_language(input_text: str) -> Tuple[str, float]:
    """Detect the language of the input text."""
    global MODEL  # pylint: disable=global-statement

    # Load the model if it hasn't been loaded yet
    if MODEL is None:
        MODEL = load_model()

    # Predict the language
    predictions = MODEL.predict(input_text, k=1)  # get top 1 prediction

    # Extract the language code from the prediction
    lang_code = predictions[0][0].split("__")[-1]
    confidence = predictions[1][0]

    return lang_code, confidence
