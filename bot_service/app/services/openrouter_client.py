import httpx

from app.core.config import settings


def ask_openrouter(prompt: str) -> str:
    if not settings.openrouter_api_key:
        return "OpenRouter API key is not configured."

    url = f"{settings.openrouter_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {
                "role": "system",
                "content": "Отвечай кратко и понятно на русском языке.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.7,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        data = response.json()
        return str(data["choices"][0]["message"]["content"])

    except httpx.HTTPStatusError as error:
        return f"OpenRouter returned error: {error.response.text}"

    except httpx.HTTPError:
        return "OpenRouter request failed."

    except (KeyError, IndexError, TypeError):
        return "Invalid OpenRouter response format."
