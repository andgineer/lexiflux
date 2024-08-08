"""AI settings views for the LexiFlux app."""

import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import render

from lexiflux.decorators import smart_login_required
from lexiflux.models import AIModelConfig, SUPPORTED_CHAT_MODELS

# Define custom captions for chat models
CHAT_MODEL_CAPTIONS = {
    "ChatOpenAI": "OpenAI (ChatGPT)",
    "ChatMistralAI": "Mistral AI",
    "ChatAnthropic": "Anthropic (Claude)",
    "Ollama": "Ollama",
}


@smart_login_required  # type: ignore
def ai_settings(request: HttpRequest) -> HttpResponse:
    """Render the AI settings page."""
    selected_tab = request.GET.get("tab", "")
    return render(request, "ai_settings.html", {"selected_tab": selected_tab})


@smart_login_required
@require_http_methods(["GET", "POST"])  # type: ignore
def ai_settings_api(request: HttpRequest) -> JsonResponse:
    """API for getting and setting AI model settings."""
    if request.method == "GET":
        configs = []
        for chat_model in SUPPORTED_CHAT_MODELS:
            config = AIModelConfig.get_or_create_ai_model_config(request.user, chat_model)
            configs.append(
                {
                    "chat_model": chat_model,
                    "caption": CHAT_MODEL_CAPTIONS.get(chat_model, chat_model),
                    "settings": config.settings,
                }
            )
        return JsonResponse(configs, safe=False)
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            errors = {}
            for config_data in data:
                chat_model = config_data["chat_model"]
                if chat_model not in SUPPORTED_CHAT_MODELS:
                    return JsonResponse(
                        {"error": f"Unsupported chat model: {chat_model}"}, status=400
                    )

                ai_model_settings = {
                    k: v
                    for k, v in config_data["settings"].items()
                    if k in SUPPORTED_CHAT_MODELS[chat_model]
                }

                try:
                    config, _ = AIModelConfig.objects.update_or_create(
                        user=request.user,
                        chat_model=chat_model,
                        defaults={"settings": ai_model_settings},
                    )
                    config.full_clean()
                except ValidationError as e:
                    errors[chat_model] = e.message_dict

            if errors:
                return JsonResponse({"errors": errors}, status=400)
            return JsonResponse({"status": "success"})
        except Exception as e:  # pylint: disable=broad-except
            return JsonResponse({"error": str(e)}, status=400)

    # This line should never be reached due to the @require_http_methods decorator,
    # but we include it to satisfy the linter and handle unexpected cases
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)
