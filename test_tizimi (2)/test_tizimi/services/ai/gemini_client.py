import logging
from typing import Optional, List, Any
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Faqat Gemini API bilan to'g'ridan-to'g'ri muloqot qiluvchi modul.
    Bazaga yozmaydi, ball hisoblamaydi, biznes mantiqqa aralashmaydi.
    Backend -> Client -> Gemini API -> raw response -> Backend.
    """
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API kaliti bo'sh bo'lishi mumkin emas")
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

    def list_models(self) -> List[str]:
        """API key uchun mavjud modellarni ro'yxatdan olish."""
        try:
            models_iter = self.client.models.list()
            names = []
            for m in models_iter:
                name = getattr(m, "name", "")
                if name.startswith("models/"):
                    name = name[len("models/"):]
                names.append(name)
            return names
        except Exception as e:
            logger.error(f"Modellarni olishda xatolik: {e}")
            raise

    def generate(
        self,
        prompt: str,
        model: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = "application/json",
        temperature: float = 0.7
    ) -> str:
        """Matn yoki strukturalashgan kontent generatsiyasi."""
        config_args = {}
        if system_instruction:
            config_args["system_instruction"] = system_instruction
        if response_mime_type:
            config_args["response_mime_type"] = response_mime_type
        if temperature is not None:
            config_args["temperature"] = temperature

        config = types.GenerateContentConfig(**config_args) if config_args else None

        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        if response and response.text:
            return response.text
        raise ValueError("Gemini bo'sh javob qaytardi")

    def analyze(
        self,
        prompt: str,
        model: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """Tahlil va xulosalar uchun generate chaqiruvi."""
        return self.generate(
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            response_mime_type=None,
            temperature=0.4
        )

    def review(
        self,
        prompt: str,
        model: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """Alohida sessiyada tekshirish va sifat tahlili."""
        return self.generate(
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2
        )
