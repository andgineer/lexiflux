"""AI settings views for the LexiFlux app."""

import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from lexiflux.models import AIModelConfig

# Define the supported chat models and their settings
SUPPORTED_CHAT_MODELS = {
    "ChatOpenAI": ["api_key", "temperature"],
    "ChatMistralAI": ["api_key", "temperature"],
    "ChatAnthropic": ["api_key", "temperature"],
    "Ollama": ["temperature"],
}


@login_required  # type: ignore
def ai_settings(request: HttpRequest) -> HttpResponse:
    """Render the AI settings page."""
    return render(request, "ai_settings.html")


@login_required  # type: ignore
@require_http_methods(["GET", "POST"])  # type: ignore
def ai_settings_api(request: HttpRequest) -> JsonResponse:
    """API for getting and setting AI model settings."""
    if request.method == "GET":
        configs = []
        for chat_model, supported_settings in SUPPORTED_CHAT_MODELS.items():
            config, created = AIModelConfig.objects.get_or_create(
                user=request.user,
                chat_model=chat_model,
                defaults={"settings": {setting: "" for setting in supported_settings}},
            )
            if created:
                config.save()
            configs.append({"chat_model": config.chat_model, "settings": config.settings})
        return JsonResponse(configs, safe=False)
    if request.method == "POST":
        try:
            data = json.loads(request.body)
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

                AIModelConfig.objects.update_or_create(
                    user=request.user,
                    chat_model=chat_model,
                    defaults={"settings": ai_model_settings},
                )
            return JsonResponse({"status": "success"})
        except Exception as e:  # pylint: disable=broad-except
            return JsonResponse({"error": str(e)}, status=400)
    # This line should never be reached due to the @require_http_methods decorator,
    # but we include it to satisfy the linter and handle unexpected cases
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)
