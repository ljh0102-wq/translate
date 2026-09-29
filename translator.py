"""번역 로직. UI(app.py)와 분리되어 있다."""

import json
import os

import openai
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
MAX_CHARS = 2000

LANGUAGES = {
    "en": "English",
    "ja": "日本語",
    "vi": "Tiếng Việt",
}

MSG_NO_KEY = ".env 파일에 OPENAI_API_KEY를 설정해주세요."
MSG_AUTH = "API 키가 올바르지 않습니다. .env 파일을 확인해주세요."
MSG_NETWORK = "인터넷 연결을 확인한 뒤 다시 시도해주세요."
MSG_RATE_LIMIT = "API 사용량 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
MSG_MODEL = "모델을 찾을 수 없습니다. .env 파일의 OPENAI_MODEL 값을 확인해주세요."
MSG_BAD_RESPONSE = "번역 결과를 처리하지 못했습니다. 다시 시도해주세요."
MSG_API_ERROR = "번역 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

SYSTEM_PROMPT = """You are a professional translator.
Detect the language of the user's text automatically and translate it into English, Japanese, and Vietnamese.

Rules:
- Preserve the original meaning, tone, and line breaks.
- Produce natural, fluent translations.
- Return only the translations, with no explanations or notes.
- If the text is already in one of the target languages, return a naturally polished version of the original for that language.

Respond with a JSON object with exactly these keys:
{"en": "<English>", "ja": "<Japanese>", "vi": "<Vietnamese>"}"""


class TranslationError(Exception):
    """사용자에게 그대로 보여줄 메시지를 담은 예외."""


def get_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or None


def get_model() -> str:
    return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def create_client() -> openai.OpenAI:
    api_key = get_api_key()
    if not api_key:
        raise TranslationError(MSG_NO_KEY)
    # SDK 기본값(600초 대기, 2회 재시도)이면 네트워크가 멈췄을 때 스피너가 수십 분 돌 수 있다.
    return openai.OpenAI(api_key=api_key, timeout=30, max_retries=1)


def translate(text: str, client: openai.OpenAI | None = None) -> dict:
    """text를 영어/일본어/베트남어로 번역해 {"en", "ja", "vi"} 형태로 반환한다.

    실패 시 사용자용 메시지를 담은 TranslationError를 발생시킨다.
    """
    if client is None:
        client = create_client()

    try:
        response = client.chat.completions.create(
            model=get_model(),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
    except openai.AuthenticationError as e:
        raise TranslationError(MSG_AUTH) from e
    except openai.RateLimitError as e:
        raise TranslationError(MSG_RATE_LIMIT) from e
    except openai.NotFoundError as e:
        raise TranslationError(MSG_MODEL) from e
    except openai.APIConnectionError as e:
        raise TranslationError(MSG_NETWORK) from e
    except openai.APIError as e:
        raise TranslationError(MSG_API_ERROR) from e

    try:
        data = json.loads(response.choices[0].message.content or "")
    except (json.JSONDecodeError, IndexError) as e:
        raise TranslationError(MSG_BAD_RESPONSE) from e

    if not isinstance(data, dict) or not all(
        isinstance(data.get(code), str) for code in LANGUAGES
    ):
        raise TranslationError(MSG_BAD_RESPONSE)

    return {code: data[code] for code in LANGUAGES}
