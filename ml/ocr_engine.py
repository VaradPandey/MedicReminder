"""
Prescription OCR Engine with Configurable Vision Providers.
Supports Google Gemini, OpenAI, OpenRouter, and Mock offline engines.
Handles image validation, preprocessing, structured transcription, and schema normalization.
"""

import os
import io
import time
import base64
import json
import re
import logging
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from image_preprocessor import preprocess_prescription_image, validate_image_file

# Automatically load ml/.env if present
load_dotenv()

logger = logging.getLogger("OCR][ENGINE")


class PrescriptionOCRError(Exception):
    """Base exception for OCR engine failures."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


# ------------------------------------------------------------------------------
# Vision Provider Interface & Implementations
# ------------------------------------------------------------------------------

class BaseVisionProvider:
    """Abstract interface for hosted multimodal vision providers."""
    def __init__(self, name: str, model_id: str, timeout: float = 30.0):
        self.name = name
        self.model_id = model_id
        self.timeout = timeout

    def call_vision(self, b64_img: str, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        """
        Calls vision API and returns (raw_text_content, finish_reason).
        Must raise PrescriptionOCRError on failure.
        """
        raise NotImplementedError


class GeminiVisionProvider(BaseVisionProvider):
    """
    Google Gemini multimodal vision provider.
    Connects to Google's official OpenAI-compatible endpoint with fast 1-4s latency.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_id = os.getenv("GEMINI_MODEL_ID", "gemini-flash-lite-latest").strip()
        self.base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        ).strip()
        super().__init__(name="gemini", model_id=self.model_id, timeout=30.0)

        if self.api_key:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout
            )
        else:
            self.client = None

    def call_vision(self, b64_img: str, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        if not self.api_key or not self.client:
            raise PrescriptionOCRError(
                "GEMINI_API_KEY is not configured in ml/.env. Please configure a valid key.",
                status_code=503
            )

        t_start = time.time()
        logger.info(f"Gemini vision request started model={self.model_id} endpoint={self.base_url}")

        try:
            resp = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=2048,
                temperature=0.0
            )
        except Exception as e:
            duration_ms = round((time.time() - t_start) * 1000)
            err_str = str(e)
            logger.error(f"Gemini vision request failed duration_ms={duration_ms} error_type={type(e).__name__}")

            if "401" in err_str or "403" in err_str or "unauthorized" in err_str.lower() or "api_key" in err_str.lower():
                raise PrescriptionOCRError(
                    "Google Gemini authentication failed. Please verify GEMINI_API_KEY in ml/.env.",
                    status_code=502
                )
            if "429" in err_str or "rate limit" in err_str.lower() or "quota" in err_str.lower():
                raise PrescriptionOCRError(
                    "Google Gemini API rate limit or quota exceeded. Please retry in a few moments.",
                    status_code=429
                )
            if "timeout" in err_str.lower() or "timed out" in err_str.lower():
                raise PrescriptionOCRError(
                    f"Google Gemini request timed out after {int(self.timeout)}s. Please retry.",
                    status_code=504
                )
            raise PrescriptionOCRError(f"Google Gemini Vision API error: {err_str}", status_code=502)

        duration_ms = round((time.time() - t_start) * 1000)

        if not resp or not getattr(resp, "choices", None) or len(resp.choices) == 0:
            raise PrescriptionOCRError("Google Gemini returned empty choices list", status_code=502)

        c0 = resp.choices[0]
        finish_reason = getattr(c0, "finish_reason", "stop") or "stop"
        msg = getattr(c0, "message", None)
        if not msg:
            raise PrescriptionOCRError("Google Gemini response did not contain a valid message", status_code=502)

        raw_content = getattr(msg, "content", "") or ""
        if not str(raw_content).strip():
            reasoning_val = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
            if isinstance(reasoning_val, str) and "{" in reasoning_val and "}" in reasoning_val:
                raw_content = reasoning_val

        logger.info(
            f"Gemini vision response received duration_ms={duration_ms} status=200 "
            f"finish_reason='{finish_reason}' content_length={len(str(raw_content))}"
        )
        return str(raw_content), finish_reason


class OpenAIVisionProvider(BaseVisionProvider):
    """
    Official OpenAI Vision API provider (e.g. gpt-4o-mini, gpt-4o).
    """
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model_id = os.getenv("OPENAI_MODEL_ID", "gpt-4o-mini").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        super().__init__(name="openai", model_id=self.model_id, timeout=30.0)

        if self.api_key:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout
            )
        else:
            self.client = None

    def call_vision(self, b64_img: str, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        if not self.api_key or not self.client:
            raise PrescriptionOCRError(
                "OPENAI_API_KEY is not configured in ml/.env. Please configure a valid key.",
                status_code=503
            )

        t_start = time.time()
        logger.info(f"OpenAI vision request started model={self.model_id}")

        try:
            resp = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=2048,
                temperature=0.0
            )
        except Exception as e:
            duration_ms = round((time.time() - t_start) * 1000)
            err_str = str(e)
            logger.error(f"OpenAI vision request failed duration_ms={duration_ms} error_type={type(e).__name__}")

            if "401" in err_str or "unauthorized" in err_str.lower():
                raise PrescriptionOCRError(
                    "OpenAI authentication failed. Please verify OPENAI_API_KEY in ml/.env.",
                    status_code=502
                )
            if "429" in err_str or "rate limit" in err_str.lower() or "quota" in err_str.lower():
                raise PrescriptionOCRError(
                    "OpenAI API rate limit or quota exceeded. Please retry in a few moments.",
                    status_code=429
                )
            if "timeout" in err_str.lower() or "timed out" in err_str.lower():
                raise PrescriptionOCRError(
                    f"OpenAI request timed out after {int(self.timeout)}s. Please retry.",
                    status_code=504
                )
            raise PrescriptionOCRError(f"OpenAI Vision API error: {err_str}", status_code=502)

        duration_ms = round((time.time() - t_start) * 1000)
        c0 = resp.choices[0]
        finish_reason = getattr(c0, "finish_reason", "stop") or "stop"
        raw_content = getattr(c0.message, "content", "") or ""
        if not str(raw_content).strip():
            reasoning_val = getattr(c0.message, "reasoning", None) or getattr(c0.message, "reasoning_content", None)
            if isinstance(reasoning_val, str) and "{" in reasoning_val and "}" in reasoning_val:
                raw_content = reasoning_val

        logger.info(
            f"OpenAI vision response received duration_ms={duration_ms} status=200 "
            f"finish_reason='{finish_reason}' content_length={len(raw_content)}"
        )
        return raw_content, finish_reason


class OpenRouterVisionProvider(BaseVisionProvider):
    """
    OpenRouter multimodal vision provider with bounded retry for transient worker limits.
    """
    def __init__(self):
        self.api_key = (
            os.getenv("VISION_API_KEY") or 
            os.getenv("OPENROUTER_API_KEY") or 
            ""
        ).strip()
        self.model_id = os.getenv(
            "VISION_MODEL_ID",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
        ).strip()
        self.base_url = os.getenv("VISION_BASE_URL", "https://openrouter.ai/api/v1").strip()
        super().__init__(name="openrouter_vision", model_id=self.model_id, timeout=75.0)

        if self.api_key:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout
            )
        else:
            self.client = None

    @staticmethod
    def _is_transient_error(err_str: str, err_code: Optional[int] = None) -> bool:
        lower = err_str.lower()
        transient_phrases = [
            "resourceexhausted",
            "worker local total request limit reached",
            "limit reached",
            "rate limit",
            "429",
            "too many requests",
            "provider_unavailable",
            "provider unavailable",
            "capacity",
            "temporarily unavailable",
            "503",
            "service unavailable",
            "502",
            "bad gateway"
        ]
        if err_code in (429, 502, 503):
            return True
        return any(phrase in lower for phrase in transient_phrases)

    def call_vision(self, b64_img: str, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        if not self.api_key or not self.client:
            raise PrescriptionOCRError("VISION_API_KEY is not configured in ml/.env", status_code=503)

        max_attempts = 2
        resp = None

        for attempt in range(1, max_attempts + 1):
            t_api_start = time.time()
            logger.info(
                f"OpenRouter vision request started attempt={attempt}/{max_attempts} "
                f"model={self.model_id} endpoint={self.base_url}"
            )

            try:
                resp = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                            ]
                        }
                    ],
                    max_tokens=4096,
                    temperature=0.0
                )
            except Exception as e:
                api_duration_ms = round((time.time() - t_api_start) * 1000)
                err_str = str(e)
                logger.error(
                    f"OpenRouter request failed attempt={attempt}/{max_attempts} "
                    f"duration_ms={api_duration_ms} error_type={type(e).__name__}"
                )

                if "401" in err_str or "unauthorized" in err_str.lower():
                    raise PrescriptionOCRError(
                        "OpenRouter authentication failed. Please verify VISION_API_KEY in ml/.env.",
                        status_code=502
                    )

                if "timeout" in err_str.lower() or "timed out" in err_str.lower():
                    raise PrescriptionOCRError(
                        f"Vision model request timed out after {int(self.timeout)}s. Please try again.",
                        status_code=504
                    )

                if attempt < max_attempts and self._is_transient_error(err_str):
                    retry_delay = 2.0
                    resp_obj = getattr(e, "response", None)
                    if resp_obj and hasattr(resp_obj, "headers"):
                        header_val = resp_obj.headers.get("retry-after")
                        if header_val and str(header_val).isdigit():
                            retry_delay = min(float(header_val), 5.0)

                    logger.warning(
                        f"Transient error on attempt 1: '{err_str[:120]}'. Retrying once in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    continue

                if "429" in err_str or "rate limit" in err_str.lower() or "resourceexhausted" in err_str.lower():
                    raise PrescriptionOCRError(
                        "OpenRouter free vision model pool is currently busy (limit reached). Please retry in a few moments.",
                        status_code=429
                    )
                raise PrescriptionOCRError(f"Upstream Vision API error: {err_str}", status_code=502)

            api_duration_ms = round((time.time() - t_api_start) * 1000)

            # Check if response payload contains provider error
            resp_error = getattr(resp, "error", None)
            if resp_error:
                err_dict = resp_error if isinstance(resp_error, dict) else getattr(resp_error, "__dict__", {})
                err_msg = str(err_dict.get("message", "Upstream provider error"))
                err_code = err_dict.get("code", 502)
                logger.warning(f"Provider returned error attempt={attempt}/{max_attempts}: {err_msg} (code={err_code})")

                if attempt < max_attempts and self._is_transient_error(err_msg, err_code):
                    retry_delay = 2.0
                    logger.warning(f"Transient provider error on attempt 1: '{err_msg[:120]}'. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue

                if "resourceexhausted" in err_msg.lower() or "limit reached" in err_msg.lower() or err_code == 429:
                    raise PrescriptionOCRError(
                        "OpenRouter free vision model pool is currently busy (worker limit reached). Please retry in a few moments.",
                        status_code=429
                    )
                raise PrescriptionOCRError(f"Vision model provider error: {err_msg}", status_code=502)

            if resp and getattr(resp, "choices", None) and len(resp.choices) > 0:
                break

            if attempt < max_attempts:
                logger.warning("Empty choices returned on attempt 1, retrying once in 2.0s...")
                time.sleep(2.0)
                continue

            raise PrescriptionOCRError("Vision model returned an empty choices list", status_code=502)

        c0 = resp.choices[0]
        finish_reason = getattr(c0, "finish_reason", "unknown") or "unknown"
        msg = getattr(c0, "message", None)
        if not msg:
            raise PrescriptionOCRError("Vision model response did not contain a valid message", status_code=502)

        if getattr(msg, "refusal", None):
            raise PrescriptionOCRError("Vision model refused to process image content", status_code=502)

        raw_content = ""
        content_val = getattr(msg, "content", None)
        if isinstance(content_val, str):
            raw_content = content_val
        elif isinstance(content_val, list):
            raw_content = "".join([
                part.get("text", "") if isinstance(part, dict) else str(getattr(part, "text", ""))
                for part in content_val
            ])
        elif content_val is not None:
            raw_content = str(content_val)

        if not raw_content.strip():
            reasoning_val = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
            if isinstance(reasoning_val, str) and "{" in reasoning_val and "}" in reasoning_val:
                raw_content = reasoning_val
            else:
                if finish_reason == "length":
                    raise PrescriptionOCRError(
                        "Vision model output was truncated (token limit reached). Please retry.",
                        status_code=502
                    )
                raise PrescriptionOCRError("Vision model returned empty text content", status_code=502)

        logger.info(
            f"OpenRouter vision response received duration_ms={api_duration_ms} status=200 "
            f"finish_reason='{finish_reason}' content_length={len(raw_content)}"
        )
        return raw_content, finish_reason


# ------------------------------------------------------------------------------
# Core Prescription OCR Engine
# ------------------------------------------------------------------------------

class PrescriptionOCREngine:
    def __init__(self):
        self.provider: Optional[BaseVisionProvider] = None
        self.reload_config()

    def reload_config(self):
        """Reload configuration and dynamically select the active vision provider."""
        load_dotenv(override=True)
        self.mock_ocr = os.getenv("MOCK_OCR", "false").lower() == "true"

        # Explicit provider setting
        configured_provider = (
            os.getenv("VISION_PROVIDER") or 
            os.getenv("OCR_ENGINE") or 
            os.getenv("OCR_PROVIDER") or 
            ""
        ).strip().lower()

        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        openrouter_key = (os.getenv("VISION_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "").strip()

        if configured_provider == "gemini":
            self.provider = GeminiVisionProvider()
            self.engine_mode = "gemini"
        elif configured_provider == "openai":
            self.provider = OpenAIVisionProvider()
            self.engine_mode = "openai"
        elif configured_provider in ("openrouter", "openrouter_vision"):
            self.provider = OpenRouterVisionProvider()
            self.engine_mode = "openrouter_vision"
        else:
            # Auto-detect in order of reliability / performance: Gemini -> OpenAI -> OpenRouter
            if gemini_key:
                self.provider = GeminiVisionProvider()
                self.engine_mode = "gemini"
            elif openai_key:
                self.provider = OpenAIVisionProvider()
                self.engine_mode = "openai"
            elif openrouter_key:
                self.provider = OpenRouterVisionProvider()
                self.engine_mode = "openrouter_vision"
            else:
                self.provider = None
                self.engine_mode = "unconfigured"

        self.vision_model_id = self.provider.model_id if self.provider else "none"
        logger.info(f"Prescription OCR Engine initialized provider={self.engine_mode} model={self.vision_model_id}")

    @property
    def client(self):
        """Compatibility property for tests mocking engine.client."""
        return getattr(self.provider, "client", None) if self.provider else None

    @client.setter
    def client(self, val):
        if self.provider:
            self.provider.client = val

    def image_to_prescription_json(self, image_path: str) -> str:
        """Convenience alias returning JSON string."""
        data = self.process_prescription(image_path)
        return json.dumps(data)

    def process_prescription(self, image_path: str) -> Dict[str, Any]:
        """
        Executes end-to-end prescription extraction via the active vision provider:
        1. Checks MOCK_OCR for fast local offline testing.
        2. Validates image file.
        3. Preprocesses image (EXIF orientation, downscaling, contrast normalization).
        4. Encodes image to base64.
        5. Calls the configured vision provider.
        6. Extracts, validates, and normalizes structured prescription entities.
        """
        t0 = time.time()

        if self.mock_ocr or os.getenv("MOCK_OCR", "false").lower() == "true":
            logger.info("MOCK_OCR enabled: returning simulated prescription data")
            return {
                "patientName": "Jane Doe",
                "doctorName": "Dr. Sarah Smith",
                "dateIssued": "24/10/2026",
                "diagnosis": "Seasonal Upper Respiratory Tract Infection",
                "medications": [
                    {
                        "name": "Amoxicillin",
                        "strength": "500mg",
                        "dosage": "1 capsule",
                        "frequency": "Three times daily",
                        "duration": "7 days",
                        "instructions": "Take with food",
                        "confidence": 0.98
                    },
                    {
                        "name": "Paracetamol",
                        "strength": "650mg",
                        "dosage": "1 tablet",
                        "frequency": "As needed (SOS)",
                        "duration": "3 days",
                        "instructions": "For fever/pain",
                        "confidence": 0.95
                    }
                ],
                "unreadable_fields": [],
                "needs_review": True,
                "engine_used": "mock",
                "model": "simulated",
                "latency_sec": 0.05
            }

        if not self.provider:
            logger.error("Vision request aborted: No vision provider configured")
            raise PrescriptionOCRError(
                "No vision provider configured. Please set GEMINI_API_KEY, OPENAI_API_KEY, or VISION_API_KEY in ml/.env.",
                status_code=503
            )

        # 1. Validate image
        is_valid, err_msg = validate_image_file(image_path)
        if not is_valid:
            logger.warning(f"Image validation failed: {err_msg}")
            raise PrescriptionOCRError(err_msg or "Invalid image file", status_code=400)

        # 2. Preprocess image
        t_prep_start = time.time()
        logger.info(f"Image preparation started path={os.path.basename(image_path)}")
        try:
            processed_img, prep_meta = preprocess_prescription_image(image_path)
            buf = io.BytesIO()
            processed_img.save(buf, format="JPEG", quality=85)
            b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
            b64_kb = round(len(b64_img) / 1024, 1)
            prep_duration_ms = round((time.time() - t_prep_start) * 1000)
            logger.info(
                f"Image preparation completed size={prep_meta.get('processed_size')} "
                f"base64_kb={b64_kb} duration_ms={prep_duration_ms}"
            )
        except Exception as e:
            logger.error(f"Image preparation error: {str(e)}")
            raise PrescriptionOCRError(f"Failed to prepare prescription image: {str(e)}", status_code=400)

        # 3. Vision API Request
        system_prompt = (
            "You are an expert medical transcriptionist specialized in handwriting OCR.\n"
            "Extract all information from the prescription image into strict JSON schema:\n"
            "{\n"
            '  "patientName": "string",\n'
            '  "doctorName": "string",\n'
            '  "dateIssued": "string",\n'
            '  "diagnosis": "string",\n'
            '  "medications": [\n'
            '    {\n'
            '      "name": "string",\n'
            '      "strength": "string",\n'
            '      "dosage": "string",\n'
            '      "frequency": "string",\n'
            '      "duration": "string",\n'
            '      "instructions": "string",\n'
            '      "confidence": 0.95\n'
            '    }\n'
            '  ],\n'
            '  "unreadable_fields": ["string"],\n'
            '  "needs_review": true\n'
            "}\n"
            "Rules:\n"
            "1. Extract ONLY visible handwriting and text. NEVER fabricate or hallucinate medicines.\n"
            "2. If a medicine line or field is unclear or illegible, add it to unreadable_fields.\n"
            "3. Normalize frequencies (e.g. 1-0-1 to 'Twice daily (Morning & Night)', 1-1-1 to 'Three times daily', 1-0-0 to 'Once daily (Morning)').\n"
            "4. Output valid JSON only, without markdown fences or extra commentary."
        )

        user_prompt = "Extract all prescription details as structured JSON"

        raw_text, finish_reason = self.provider.call_vision(
            b64_img=b64_img,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # 4. Parse model response into structured dictionary
        logger.info("Parsing structured response started")
        structured_data = self._parse_json_response(raw_text, finish_reason=finish_reason)

        # 5. Normalize and enforce safety constraints
        medications = structured_data.get("medications", [])
        if not isinstance(medications, list):
            medications = []

        normalized_meds = []
        for m in medications:
            if isinstance(m, dict) and m.get("name"):
                normalized_meds.append({
                    "name": str(m.get("name", "")).strip(),
                    "strength": str(m.get("strength") or "").strip(),
                    "dosage": str(m.get("dosage") or "").strip(),
                    "frequency": str(m.get("frequency") or "").strip(),
                    "duration": str(m.get("duration") or "").strip(),
                    "instructions": str(m.get("instructions") or "").strip(),
                    "confidence": float(m.get("confidence") or 0.9)
                })

        unreadable = structured_data.get("unreadable_fields", [])
        if not isinstance(unreadable, list):
            unreadable = [str(unreadable)] if unreadable else []

        if len(normalized_meds) == 0 and len(unreadable) == 0:
            unreadable.append("No clear handwritten medication entries recognized. Please verify manually.")

        total_latency = round(time.time() - t0, 2)
        logger.info(
            f"Parsing structured response completed medicines_count={len(normalized_meds)} "
            f"unreadable_count={len(unreadable)} duration_sec={total_latency}"
        )

        return {
            "patientName": str(structured_data.get("patientName") or "").strip(),
            "doctorName": str(structured_data.get("doctorName") or "").strip(),
            "dateIssued": str(structured_data.get("dateIssued") or "").strip(),
            "diagnosis": str(structured_data.get("diagnosis") or "").strip(),
            "medications": normalized_meds,
            "unreadable_fields": unreadable,
            "needs_review": True,
            "engine_used": self.engine_mode,
            "model": self.provider.model_id,
            "latency_sec": total_latency
        }

    def _parse_json_response(self, text: str, finish_reason: str = "stop") -> Dict[str, Any]:
        """Extract and parse JSON object from model response, handling markdown fences, preambles, and minor syntax quirks."""
        if not text or not text.strip():
            raise PrescriptionOCRError("Vision model returned empty text content", status_code=502)

        # Strategy 1: Direct JSON parse
        try:
            parsed = json.loads(text.strip(), strict=False)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Strategy 2: Extract from markdown code fences (```json ... ``` or ``` ... ```)
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            fence_candidate = fence_match.group(1).strip()
            try:
                parsed = json.loads(fence_candidate, strict=False)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            # Try sanitizing trailing commas within fence candidate
            sanitized = re.sub(r",\s*([\]\}])", r"\1", fence_candidate)
            try:
                parsed = json.loads(sanitized, strict=False)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        # Strategy 3: Outermost braces {...}
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = text[start_idx:end_idx + 1].strip()
            try:
                parsed = json.loads(candidate, strict=False)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

            # Strategy 4: Clean trailing commas
            sanitized = re.sub(r",\s*([\]\}])", r"\1", candidate)
            try:
                parsed = json.loads(sanitized, strict=False)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        # If we reach here, JSON could not be parsed
        if finish_reason == "length":
            logger.warning("Failed to parse JSON and finish_reason was 'length' (response truncated)")
            raise PrescriptionOCRError(
                "Vision model response was truncated before completion (token limit reached). Please retry with a clearer or cropped image.",
                status_code=502
            )

        has_braces = (text.find("{") != -1 and text.rfind("}") != -1)
        logger.error(f"Structured JSON could not be parsed from model output length={len(text)} has_braces={has_braces}")
        raise PrescriptionOCRError("Failed to parse structured JSON from vision model response", status_code=502)
