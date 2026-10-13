import os
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dotenv import load_dotenv

from services.ai.gemini_client import GeminiClient
from services.ai.audit_log import AIAuditLog

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
logger = logging.getLogger(__name__)

class AIGateway:
    """
    Barcha AI so'rovlari uchun yagona darvoza (AI Gateway).
    Boshqaradi: API key, model tanlash (models.list orqali), retry (3 marta),
    xatolarni audit qilish, latency hisoblash va fallback siyosati.
    """
    _cached_models: Optional[List[str]] = None
    _selected_model: Optional[str] = None
    _client_instance: Optional[GeminiClient] = None

    PREFERRED_MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest"
    ]

    @classmethod
    def get_api_key(cls) -> str:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            load_dotenv(dotenv_path=ENV_PATH)
            key = os.getenv("GEMINI_API_KEY", "").strip()
        return key

    @classmethod
    def set_api_key(cls, key: str):
        key = key.strip()
        os.environ["GEMINI_API_KEY"] = key
        cls._client_instance = None
        cls._cached_models = None
        cls._selected_model = None

        env_path = str(ENV_PATH)
        lines = []
        key_found = False
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if line.startswith("GEMINI_API_KEY="):
                    lines[i] = f"GEMINI_API_KEY={key}\n"
                    key_found = True
                    break
        if not key_found:
            lines.append(f"\nGEMINI_API_KEY={key}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    @classmethod
    def get_client(cls) -> GeminiClient:
        key = cls.get_api_key()
        if not key:
            raise ValueError("Gemini API kaliti kiritilmagan. Sozlamalardan API kalitini kiriting.")
        if cls._client_instance is None or cls._client_instance.api_key != key:
            cls._client_instance = GeminiClient(api_key=key)
        return cls._client_instance

    @classmethod
    def get_available_models(cls) -> List[str]:
        """API key uchun mavjud modellarni tekshirish (models.list)."""
        if cls._cached_models:
            return cls._cached_models
        client = cls.get_client()
        try:
            models = client.list_models()
            cls._cached_models = models
            return models
        except Exception as e:
            logger.error(f"models.list chaqirishda xatolik: {e}")
            raise

    @classmethod
    def resolve_model(cls) -> str:
        """
        Model nomini aniqlash. Mavjud eng barqaror va tezkor modelni tanlaydi.
        """
        if cls._selected_model:
            return cls._selected_model

        try:
            available = cls.get_available_models()
            for pref in cls.PREFERRED_MODELS:
                if pref in available:
                    cls._selected_model = pref
                    return pref
            for m in available:
                if "flash" in m.lower():
                    cls._selected_model = m
                    return m
            if available:
                cls._selected_model = available[0]
                return available[0]
        except Exception as e:
            logger.warning(f"Modellarni ro'yxatdan olishda ogohlantirish: {e}")

        cls._selected_model = "gemini-2.5-flash"
        return cls._selected_model

    @classmethod
    def execute_with_retry(
        cls,
        task_func: Callable[[GeminiClient, str], Any],
        task_name: str,
        request_data: Any,
        user_id: Optional[int] = None,
        max_retries: int = 3,
        fallback_allowed: bool = False,
        fallback_func: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        AI so'rovini 3 martagacha qayta urinish bilan bajarish.
        Xato oqimi: Gemini -> ERROR -> retry -> 2-urinish -> 3-urinish -> xato / fallback.
        """
        last_error = None
        start_time = time.time()
        client = None
        model_name = "unknown"

        try:
            client = cls.get_client()
            model_name = cls.resolve_model()
        except Exception as e:
            last_error = str(e)
            latency = time.time() - start_time
            AIAuditLog.log(
                task=task_name,
                model=model_name,
                request_data=request_data,
                response_data=None,
                status="error",
                latency=latency,
                error=last_error,
                user_id=user_id
            )
            if fallback_allowed and fallback_func:
                return fallback_func()
            raise RuntimeError(f"Gemini API xatosi / model mavjud emas: {last_error}")

        # Faqat tasdiqlangan mavjud modellardan foydalanamiz
        available = []
        try:
            available = cls.get_available_models()
        except Exception:
            pass

        active_model = cls.resolve_model()
        candidate_models = [active_model]
        if available:
            for pref in cls.PREFERRED_MODELS:
                if pref in available and pref not in candidate_models:
                    candidate_models.append(pref)
            for m in available:
                if "flash" in m.lower() and m not in candidate_models:
                    candidate_models.append(m)
        else:
            candidate_models = [active_model]
        # Takrorlanmas qilib tartiblash
        seen_cand = []
        for c in candidate_models:
            if c and c not in seen_cand:
                seen_cand.append(c)

        for attempt in range(1, max_retries + 1):
            cur_model = seen_cand[(attempt - 1) % len(seen_cand)]
            try:
                result = task_func(client, cur_model)
                latency = time.time() - start_time
                cls._selected_model = cur_model
                AIAuditLog.log(
                    task=task_name,
                    model=cur_model,
                    request_data=request_data,
                    response_data=result,
                    status="success",
                    latency=latency,
                    user_id=user_id
                )
                return result
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{task_name}] {attempt}-urinishda ({cur_model}) xatolik: {e}")
                time.sleep(0.5 * attempt)

        latency = time.time() - start_time
        AIAuditLog.log(
            task=task_name,
            model=model_name,
            request_data=request_data,
            response_data=None,
            status="error",
            latency=latency,
            error=last_error,
            user_id=user_id
        )

        if fallback_allowed and fallback_func:
            return fallback_func()

        raise RuntimeError(f"AI generatsiya xatosi (3 urinishdan keyin ham o'xshamadi): {last_error}")
