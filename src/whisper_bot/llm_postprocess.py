"""LLM-based text postprocessing for punctuation and spelling correction."""

import httpx
import logging

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """Ты корректор текста. Исправь пунктуацию и орфографию в тексте транскрипции голосового сообщения.

Правила:
- Добавь знаки препинания (точки, запятые, вопросительные и восклицательные знаки)
- Исправь очевидные орфографические ошибки
- Разбей на предложения
- НЕ меняй смысл и слова
- НЕ добавляй ничего от себя
- Верни ТОЛЬКО исправленный текст, без комментариев"""


async def postprocess_with_llm(
    text: str,
    api_key: str,
    model: str = "llama-3.3-70b-versatile",
) -> str:
    """Add punctuation and fix spelling using Groq LLM.

    Args:
        text: Raw transcription text without punctuation
        api_key: Groq API key
        model: LLM model to use

    Returns:
        Text with punctuation and spelling corrections
    """
    if not text or len(text.strip()) < 10:
        # Skip very short texts
        return text

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            },
        )

        if response.status_code != 200:
            logger.warning(f"LLM postprocess error {response.status_code}: {response.text}")
            return text  # Return original on error

        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()

        # Sanity check: result shouldn't be drastically different in length
        if len(result) < len(text) * 0.5 or len(result) > len(text) * 2:
            logger.warning("LLM output length mismatch, returning original")
            return text

        return result
