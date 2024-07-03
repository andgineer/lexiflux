"""Lexical articles."""

from lexiflux.llm import Llm


class LexicalArticles:
    """Lexical articles."""

    # todo: add translator articles
    def __init__(self) -> None:
        self.llm = Llm()

    def get_article(  # pylint: disable=too-many-arguments
        self, article_name: str, text: str, word: str, source_language: str, target_language: str
    ) -> str:
        """Create the article."""
        if article_name in self.llm.article_names():
            return self.llm.get_article(
                article_name,
                {},
                {
                    "text": text,
                    "word": word,
                    "source_language": source_language,
                    "target_language": target_language,
                },
            )
        raise ValueError(f"Article '{article_name}' not found.")

    def article_names(self) -> list[str]:
        """Get a list of all available article names."""
        return self.llm.article_names()
