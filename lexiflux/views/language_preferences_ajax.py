"""Views for the language preferences editor page and Ajax."""

import json
from typing import Any, Dict, Optional
import logging

from deep_translator.exceptions import LanguageNotSupportedException
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from lexiflux.language.llm import Llm
from lexiflux.language.translation import Translator, get_translator
from lexiflux.models import (
    Language,
    LexicalArticleType,
    LanguagePreferences,
    LEXICAL_ARTICLE_PARAMETERS,
    LexicalArticle,
)


logger = logging.getLogger()


@login_required  # type: ignore
def language_preferences_editor(request: HttpRequest) -> HttpResponse:
    """Language preferences editor."""
    language_preferences = (
        request.user.default_language_preferences
        or request.user.language_preferences.all().first()
    )
    all_languages = Language.objects.all()

    articles = (
        list(
            language_preferences.get_lexical_articles().values("id", "title", "type", "parameters")
        )
        if language_preferences
        else []
    )
    all_languages_data = list(all_languages.values("google_code", "name"))

    articles_json = json.dumps(articles)
    all_languages_json = json.dumps(all_languages_data)
    inline_translation_json = json.dumps(language_preferences.inline_translation)

    llm = Llm()
    ai_models = [
        {"key": key, "title": value["title"], "suffix": value["suffix"]}
        for key, value in llm.chat_models.items()
    ]
    translators = Translator.available_translators()

    context = {
        "user": request.user,
        "language_preferences": language_preferences,
        "articles": articles_json,
        "all_languages": all_languages_json,
        "default_language_preferences": language_preferences,
        "inline_translation": inline_translation_json,
        "lexical_article_types": LexicalArticleType.choices,
        "ai_models": json.dumps(ai_models),
        "translators": json.dumps(translators),
    }

    return render(request, "language-preferences.html", context)


@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def get_language_preferences(request: HttpRequest) -> JsonResponse:
    """Ajax to Change or create a new preferences for the selected language."""
    try:
        data = json.loads(request.body)
        language_id = data.get("language_id")
        language = get_object_or_404(Language, google_code=language_id)

        language_preferences = LanguagePreferences.get_or_create_language_preferences(
            request.user, language
        )

        return JsonResponse(
            {
                "status": "success",
                "language_preferences_id": language_preferences.id,
                "articles": list(
                    language_preferences.get_lexical_articles().values(
                        "id", "title", "type", "parameters"
                    )
                ),
                "inline_translation": language_preferences.inline_translation,
                "user_language_id": language_preferences.user_language.google_code
                if language_preferences.user_language
                else None,
            }
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Error in get_language_preferences")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def update_user_language(request: HttpRequest) -> JsonResponse:
    """Ajax to Update the user language."""
    try:
        data = json.loads(request.body)
        language_id = data.get("language_id")
        language_preferences_language_id = data.get("language_preferences_language_id")

        language = get_object_or_404(Language, google_code=language_id)
        language_preferences = get_object_or_404(
            LanguagePreferences,
            user=request.user,
            language__google_code=language_preferences_language_id,
        )

        language_preferences.user_language = language
        language_preferences.save()

        return JsonResponse({"status": "success"})
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"status": "error", "message": str(e)})


def check_article_params(
    article_type: str, parameters: Dict[str, str], language_preferences: LanguagePreferences
) -> Optional[JsonResponse]:
    """Check if the article parameters are valid.

    Return None if the parameters are valid, otherwise return a JsonResponse with an error message.
    """
    if article_type == "Dictionary":
        if not parameters.get("dictionary"):
            return JsonResponse(
                {"status": "error", "message": "Please select a dictionary"}, status=400
            )
        try:
            get_translator(
                parameters.get("dictionary"),
                language_preferences.language.name.lower(),
                language_preferences.user_language.name.lower(),
            ).translate("test")
        except LanguageNotSupportedException:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"{parameters.get('dictionary')} cannot translate "
                    f"from {language_preferences.language.name} "
                    f"to {language_preferences.user_language.name}",
                },
                status=400,
            )
    return None


@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def save_inline_translation(request: HttpRequest) -> JsonResponse:
    """Ajax to Save the inline translation settings."""
    data = json.loads(request.body)
    language_id = data.get("language_id")
    translation_type = data.get("type")
    parameters = data.get("parameters", {})

    language_preferences = request.user.language_preferences.get(language__google_code=language_id)
    if error_response := check_article_params(translation_type, parameters, language_preferences):
        return error_response

    # Filter the parameters to only include valid ones for the selected type
    filtered_parameters = {
        k: v
        for k, v in parameters.items()
        if k in LEXICAL_ARTICLE_PARAMETERS.get(translation_type, [])
    }

    language_preferences.inline_translation_type = translation_type
    language_preferences.inline_translation_parameters = filtered_parameters
    language_preferences.save()

    return JsonResponse(
        {
            "status": "success",
            "inline_translation": language_preferences.inline_translation,
        }
    )


@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def manage_lexical_article(request: HttpRequest) -> JsonResponse:  # pylint: disable=too-many-return-statements
    """Ajax to Add, edit, or delete a lexical article."""
    try:
        data = json.loads(request.body)
        action = data.get("action")
        language_id = data.get("language_id")

        logger.debug(f"Received request: action={action}, language_id={language_id}")

        if not language_id:
            return JsonResponse(
                {"status": "error", "message": "Language ID is missing"}, status=400
            )

        try:
            language = Language.objects.get(google_code=language_id)
            language_preferences = LanguagePreferences.objects.get(
                user=request.user, language=language
            )
        except Language.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Language not found"}, status=404)
        except LanguagePreferences.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Preferences not found for this language"},
                status=404,
            )

        if action == "add":
            return add_lexical_article(language_preferences, data)
        if action == "edit":
            return edit_lexical_article(language_preferences, data)
        if action == "delete":
            return delete_lexical_article(language_preferences, data)
        return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)

    except json.JSONDecodeError:
        logger.exception("Invalid JSON in request body")
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON in request body"}, status=400
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("An unexpected error occurred in manage_lexical_article")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required  # type: ignore
def add_lexical_article(
    language_preferences: LanguagePreferences, data: dict[str, Any]
) -> JsonResponse:
    """Ajax to Add a lexical article."""
    try:
        if error_response := check_article_params(
            data["type"], data["parameters"], language_preferences
        ):
            return error_response

        article = LexicalArticle.objects.create(
            language_preferences=language_preferences,
            type=data["type"],
            title=data["title"],
            parameters=data["parameters"],
        )
        return JsonResponse({"status": "success", "id": article.id})
    except IntegrityError:
        return JsonResponse(
            {"status": "error", "message": "An article with this title already exists"}, status=400
        )
    except KeyError as e:
        return JsonResponse(
            {"status": "error", "message": f"Missing required field: {str(e)}"}, status=400
        )


@login_required  # type: ignore
def edit_lexical_article(
    language_preferences: LanguagePreferences, data: dict[str, Any]
) -> JsonResponse:
    """Ajax to Edit a lexical article."""
    try:
        article_id = data.get("id")
        if not article_id:
            return JsonResponse(
                {"status": "error", "message": "Article ID is missing"}, status=400
            )

        article = LexicalArticle.objects.filter(
            id=article_id, language_preferences=language_preferences
        ).first()
        if not article:
            return JsonResponse({"status": "error", "message": "Article not found"}, status=404)

        if error_response := check_article_params(
            data["type"], data["parameters"], language_preferences
        ):
            return error_response

        article.type = data.get("type", article.type)
        article.title = data.get("title", article.title)
        article.parameters = data.get("parameters", article.parameters)
        article.full_clean()  # Validate the model
        article.save()
        return JsonResponse({"status": "success", "id": article.id})
    except ValidationError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception(f"Error editing article: {str(e)}")
        return JsonResponse({"status": "error", "message": "Failed to edit article"}, status=500)


@login_required  # type: ignore
def delete_lexical_article(
    language_preferences: LanguagePreferences, data: dict[str, Any]
) -> JsonResponse:
    """Ajax to Delete a lexical article."""
    try:
        article_id = data.get("id")
        if not article_id:
            return JsonResponse(
                {"status": "error", "message": "Article ID is missing"}, status=400
            )

        article = LexicalArticle.objects.get(
            id=article_id, language_preferences=language_preferences
        )
        article.delete()
        return JsonResponse({"status": "success"})
    except LexicalArticle.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Article not found"}, status=404)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception(f"Error deleting article: {str(e)}")
        return JsonResponse({"status": "error", "message": "Failed to delete article"}, status=500)