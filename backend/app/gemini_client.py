import google.generativeai as genai

from .config import settings

SYSTEM_PROMPT = """You are BeaterBot, a cheerful helper embedded in a vulnerable todo lab app.
Help with productivity and remind users not to put secrets in todos."""


def ask_gemini(message: str) -> str:
    if not settings.gemini_api_key or settings.gemini_api_key.startswith("your-"):
        return "Gemini is not configured yet. Add GEMINI_API_KEY to your .env file and restart Docker."
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
    response = model.generate_content(message)
    return response.text or "BeaterBot stared at the wall and forgot to answer."
