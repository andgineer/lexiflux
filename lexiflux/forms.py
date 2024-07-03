"""Forms for the Lexiflux app."""

from typing import Dict, Any

from django import forms
from .models import LexicalArticle


class LexicalArticleForm(forms.ModelForm):  # type: ignore
    """Form for creating a lexical article."""

    class Meta:
        model = LexicalArticle
        fields = ["type", "title", "parameters"]

    def clean(self) -> Dict[str, Any]:
        cleaned_data = super().clean()
        article_type = cleaned_data.get("type")
        parameters = cleaned_data.get("parameters")

        if article_type == "Site":
            if "url" not in parameters or "window" not in parameters:
                raise forms.ValidationError(
                    "Site article must have 'url' and 'window' parameters."
                )
        elif article_type == "Dictionary":
            if "dictionary" not in parameters:
                raise forms.ValidationError("Dictionary article must have 'dictionary' parameter.")
        elif article_type not in ["Dictionary", "Site"]:
            if "model" not in parameters:
                raise forms.ValidationError(f"{article_type} article must have 'model' parameter.")

        return cleaned_data  # type: ignore
