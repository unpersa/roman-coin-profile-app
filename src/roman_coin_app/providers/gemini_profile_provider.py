from __future__ import annotations

import os
from google.genai import types
import random
import re

import time

from roman_coin_app.config import Settings, get_secret
from roman_coin_app.profile_schemas import (
    HistoricalContextDraft,
    ProfileInference,
    ProfileVisualEvidence,
)
from roman_coin_app.utils import extract_json_object, normalize_list, safe_int


PROFILE_SYSTEM_PROMPT = """
You are a multimodal assistant specialised in Roman numismatics.

You will receive two photographs of the SAME physical coin:
1. OBVERSE
2. REVERSE

The product goal is NOT to force an exact RIC identification.
The goal is to create a reliable numismatic profile that can later be
enriched with museum, archaeological and linked-data sources.

STAGE A — DIRECT VISUAL OBSERVATION
Report only what is genuinely visible:
- legible letter fragments;
- exergue / mintmark / field marks;
- bust features;
- reverse iconography.

Do not autocomplete unreadable letters from memory.

STAGE B — NUMISMATIC PROFILE
Infer, when evidence allows:
- authority / emperor;
  IMPORTANT: `profile.authority` must contain ONE single most probable
  canonical ruler/authority name only.
  Never put alternatives, slashes, parenthetical "or" expressions, or
  multiple rulers in `profile.authority`.
  If another authority is plausible, keep the best-supported ruler in
  `profile.authority` and place alternative names in `uncertainties`;
- dynasty;
- period and approximate dates;
- denomination;
- material;
- mint;
- reconstructed legends and descriptions.

Give a separate confidence score from 0 to 1 for each important field.

STAGE C — HISTORICAL CONTEXT
Provide a short, cautious historical context (2–4 sentences) about the
probable authority and period. Do NOT claim museum holdings, hoards,
findspots, auction records or database facts. Those will be retrieved
from external sources later.

RIC RULE
- An exact RIC reference is NOT required.
- Do not state that an exact RIC has been identified.
- possible_references may be empty.
- If you suggest references, treat them as tentative hypotheses only.


LANGUAGE POLICY — SPANISH USER-FACING TEXT
- All free-text explanatory content shown to the user MUST be written in Spanish.
- Write observed_bust and observed_reverse_iconography in Spanish.
- Write obverse_description and reverse_description in Spanish.
- Write historical_context fields in Spanish.
- Write uncertainties and identification_basis in Spanish.
- Preserve visible and reconstructed coin legends in their original Latin; do not translate inscriptions.
- Keep controlled identification values such as authority, mint, denomination and material in a standard canonical numismatic form when that improves linked-data reconciliation. The UI will localize those controlled labels to Spanish.

Other rules:
- Do not browse the web.
- Do not use OCRE, Nomisma or external tools.
- Do not invent unreadable letters.
- Separate direct observation from inference.
- Express uncertainty explicitly.
- Return ONLY JSON.
"""


PROFILE_USER_PROMPT = """
Return exactly one JSON object with this structure:

{
  "visual_evidence": {
    "visible_obverse_fragments": [],
    "visible_reverse_fragments": [],
    "exergue_or_mintmark": "",
    "observed_bust": "",
    "observed_reverse_iconography": ""
  },

  "profile": {
    "authority": "",
    "dynasty": "",
    "period": "",
    "date_min": null,
    "date_max": null,
    "denomination": "",
    "material": "",
    "mint": "",
    "obverse_legend": "",
    "obverse_description": "",
    "reverse_legend": "",
    "reverse_description": ""
  },

  "field_confidence": {
    "authority": 0.0,
    "dynasty": 0.0,
    "period": 0.0,
    "date_range": 0.0,
    "denomination": 0.0,
    "material": 0.0,
    "mint": 0.0,
    "obverse_legend": 0.0,
    "reverse_legend": 0.0
  },

  "overall_confidence": 0.0,

  "possible_references": [],

  "historical_context": {
    "summary": "",
    "authority_context": "",
    "period_context": ""
  },

  "uncertainties": [],
  "identification_basis": []
}
"""


def _safe_float(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    return max(
        0.0,
        min(1.0, value),
    )







_GEMINI_RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}

# Funcionamiento normal del producto.
# El smoke de NB34 lo baja temporalmente a 1.
_GEMINI_OUTER_MAX_ATTEMPTS = max(1, int(os.getenv("ROMAN_COIN_GEMINI_MAX_ATTEMPTS", "3")))
_GEMINI_FALLBACK_MAX_ATTEMPTS = max(
    1,
    int(os.getenv("ROMAN_COIN_GEMINI_FALLBACK_MAX_ATTEMPTS", "1")),
)

_GEMINI_RETRY_BASE_SECONDS = 10.0
_GEMINI_RETRY_MAX_SECONDS = 30.0
_GEMINI_RETRY_JITTER_SECONDS = 1.5


def _gemini_error_text(
    error,
) -> str:
    return (
        f"{type(error).__name__}: {error}"
    )


def _gemini_error_status_code(
    error,
):
    for attribute in (
        "status_code",
        "code",
    ):
        value = getattr(
            error,
            attribute,
            None,
        )

        try:
            value = int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            value = None

        if (
            value is not None
            and 100 <= value <= 599
        ):
            return value

    text = _gemini_error_text(
        error
    )

    match = re.search(
        r"(?<!\d)(429|500|502|503|504)(?!\d)",
        text,
    )

    if match:
        return int(
            match.group(
                1
            )
        )

    return None


def _is_explicit_daily_free_tier_quota(
    error,
) -> bool:
    text = (
        _gemini_error_text(
            error
        )
        .lower()
    )

    compact = re.sub(
        r"[^a-z0-9]+",
        "",
        text,
    )

    exact_daily_markers = (
        "generaterequestsperdayperprojectpermodelfreetier",
        "generaterequestsperdayperprojectpermodel",
        "requestsperdayperprojectpermodel",
        "perdayperprojectpermodel",
    )

    if any(
        marker in compact
        for marker in exact_daily_markers
    ):
        return True

    spaced_daily_markers = (
        "daily quota",
        "requests per day",
        "per-day quota",
        "per day per project",
    )

    return any(
        marker in text
        for marker in spaced_daily_markers
    )


def _call_gemini_with_outer_retry(
    call,
    *args,
    max_attempts=None,
    **kwargs,
):
    last_error = None
    configured_attempts = (
        _GEMINI_OUTER_MAX_ATTEMPTS
        if max_attempts is None
        else max(1, int(max_attempts))
    )

    for attempt in range(
        1,
        configured_attempts + 1,
    ):
        try:
            if attempt > 1:
                print(
                    "Gemini: reintento de aplicación "
                    f"{attempt}/{configured_attempts}..."
                )

            return call(
                *args,
                **kwargs,
            )

        except Exception as error:
            last_error = error

            status_code = (
                _gemini_error_status_code(
                    error
                )
            )

            daily_free_quota = (
                status_code == 429
                and _is_explicit_daily_free_tier_quota(
                    error
                )
            )

            if daily_free_quota:
                print(
                    "Gemini 429: CUOTA DIARIA DEL FREE TIER AGOTADA."
                )
                print(
                    "QuotaId detectado: "
                    "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
                )
                print(
                    "No se realizará ningún reintento automático."
                )
                raise

            retryable = (
                status_code
                in _GEMINI_RETRYABLE_STATUS_CODES
            )

            if (
                not retryable
                or attempt
                >= configured_attempts
            ):
                if retryable:
                    print(
                        "Gemini: no quedan más intentos "
                        "de aplicación para esta ejecución."
                    )

                raise

            delay = min(
                _GEMINI_RETRY_MAX_SECONDS,
                (
                    _GEMINI_RETRY_BASE_SECONDS
                    * (
                        2
                        ** (
                            attempt - 1
                        )
                    )
                ),
            )

            delay += random.uniform(
                0.0,
                _GEMINI_RETRY_JITTER_SECONDS,
            )

            print(
                "Gemini error transitorio "
                f"HTTP {status_code}. "
                f"Nuevo intento en {delay:.1f} s."
            )

            time.sleep(
                delay
            )

    raise last_error


class _RetryingModelsProxy:
    def __init__(
        self,
        models,
    ):
        self._models = models

    def generate_content(
        self,
        *args,
        **kwargs,
    ):
        return _call_gemini_with_outer_retry(
            self._models.generate_content,
            *args,
            **kwargs,
        )

    def generate_content_with_attempts(
        self,
        *args,
        max_attempts,
        **kwargs,
    ):
        return _call_gemini_with_outer_retry(
            self._models.generate_content,
            *args,
            max_attempts=max_attempts,
            **kwargs,
        )

    def __getattr__(
        self,
        name,
    ):
        return getattr(
            self._models,
            name,
        )


class _RetryingGenAIClient:
    def __init__(
        self,
        client,
    ):
        self._client = client
        self.models = (
            _RetryingModelsProxy(
                client.models
            )
        )

    def __getattr__(
        self,
        name,
    ):
        return getattr(
            self._client,
            name,
        )


class GeminiProfileProvider:
    def __init__(
        self,
        settings: Settings | None = None,
    ):
        self.settings = (
            settings
            or Settings.from_environment()
        )

        api_key = get_secret("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "No está configurado GEMINI_API_KEY."
            )

        from google import genai

        self.client = _RetryingGenAIClient(
            genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(
                        attempts=1,
                    ),
                ),
            )
        )

    @staticmethod
    def _part(data: bytes, mime_type: str):
        from google.genai import types

        return types.Part.from_bytes(
            data=data,
            mime_type=mime_type,
        )

    def analyze(
        self,
        obverse_bytes: bytes,
        reverse_bytes: bytes,
        obverse_mime: str = "image/jpeg",
        reverse_mime: str = "image/jpeg",
    ) -> ProfileInference:
        from google.genai import types

        started = time.perf_counter()

        contents = [
            PROFILE_SYSTEM_PROMPT,
            "OBVERSE:",
            self._part(
                obverse_bytes,
                obverse_mime,
            ),
            "REVERSE:",
            self._part(
                reverse_bytes,
                reverse_mime,
            ),
            PROFILE_USER_PROMPT,
        ]
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )
        used_model = self.settings.gemini_model
        fallback_used = False

        try:
            response = self.client.models.generate_content(
                model=used_model,
                contents=contents,
                config=config,
            )
        except Exception as primary_error:
            fallback_model = self.settings.gemini_fallback_model
            if not (
                _gemini_error_status_code(primary_error) == 503
                and fallback_model
                and fallback_model != used_model
            ):
                raise

            print(
                f"Gemini principal {used_model} no disponible tras "
                "agotar reintentos."
            )
            print(f"Intentando fallback {fallback_model}...")
            used_model = fallback_model
            try:
                response = self.client.models.generate_content_with_attempts(
                    model=used_model,
                    contents=contents,
                    config=config,
                    max_attempts=_GEMINI_FALLBACK_MAX_ATTEMPTS,
                )
            except Exception as fallback_error:
                raise fallback_error from primary_error
            fallback_used = True
            print(f"Gemini fallback completado con {used_model}.")

        raw_text = (
            response.text
            if getattr(response, "text", None)
            else ""
        )

        payload = extract_json_object(raw_text)

        visual = (
            payload.get("visual_evidence", {})
            or {}
        )

        profile = (
            payload.get("profile", {})
            or {}
        )

        historical = (
            payload.get("historical_context", {})
            or {}
        )

        raw_confidence = (
            payload.get("field_confidence", {})
            or {}
        )

        field_confidence = {
            str(key): _safe_float(value)
            for key, value
            in raw_confidence.items()
        }

        return ProfileInference(
            evidence=ProfileVisualEvidence(
                visible_obverse_fragments=normalize_list(
                    visual.get("visible_obverse_fragments")
                ),
                visible_reverse_fragments=normalize_list(
                    visual.get("visible_reverse_fragments")
                ),
                exergue_or_mintmark=str(
                    visual.get("exergue_or_mintmark", "")
                    or ""
                ),
                observed_bust=str(
                    visual.get("observed_bust", "")
                    or ""
                ),
                observed_reverse_iconography=str(
                    visual.get(
                        "observed_reverse_iconography",
                        "",
                    )
                    or ""
                ),
            ),
            authority=str(
                profile.get("authority", "")
                or ""
            ),
            dynasty=str(
                profile.get("dynasty", "")
                or ""
            ),
            period=str(
                profile.get("period", "")
                or ""
            ),
            date_min=safe_int(
                profile.get("date_min")
            ),
            date_max=safe_int(
                profile.get("date_max")
            ),
            denomination=str(
                profile.get("denomination", "")
                or ""
            ),
            material=str(
                profile.get("material", "")
                or ""
            ),
            mint=str(
                profile.get("mint", "")
                or ""
            ),
            obverse_legend=str(
                profile.get("obverse_legend", "")
                or ""
            ),
            obverse_description=str(
                profile.get("obverse_description", "")
                or ""
            ),
            reverse_legend=str(
                profile.get("reverse_legend", "")
                or ""
            ),
            reverse_description=str(
                profile.get("reverse_description", "")
                or ""
            ),
            field_confidence=field_confidence,
            overall_confidence=_safe_float(
                payload.get("overall_confidence")
            ),
            possible_references=normalize_list(
                payload.get("possible_references")
            ),
            uncertainties=normalize_list(
                payload.get("uncertainties")
            ),
            identification_basis=normalize_list(
                payload.get("identification_basis")
            ),
            historical_context=HistoricalContextDraft(
                summary=str(
                    historical.get("summary", "")
                    or ""
                ),
                authority_context=str(
                    historical.get(
                        "authority_context",
                        "",
                    )
                    or ""
                ),
                period_context=str(
                    historical.get(
                        "period_context",
                        "",
                    )
                    or ""
                ),
            ),
            provider=used_model,
            fallback_used=fallback_used,
            raw_text=raw_text,
            latency_seconds=(
                time.perf_counter()
                - started
            ),
        )
