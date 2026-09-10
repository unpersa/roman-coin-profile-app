from pathlib import Path
from types import SimpleNamespace
import sys
import types
import unittest
from unittest.mock import patch

# Keep these tests hermetic when the optional Google SDK is not installed.
if "google.genai" not in sys.modules:
    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_module.types = SimpleNamespace(
        GenerateContentConfig=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    google_module.genai = genai_module
    sys.modules.setdefault("google", google_module)
    sys.modules.setdefault("google.genai", genai_module)

from roman_coin_app.cache_policy import should_persist_profile_result
from roman_coin_app.config import Settings
from roman_coin_app.providers import gemini_profile_provider as provider_module


class GeminiError(RuntimeError):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = {model: list(values) for model, values in outcomes.items()}
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        outcome = self.outcomes[model].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


def make_provider(outcomes):
    settings = Settings(
        project_dir=Path("."),
        processed_dir=Path("."),
        cache_dir=Path("."),
        gemini_model="gemini-3.7-flash",
        gemini_verifier_model="gemini-3.7-flash",
        gemini_fallback_model="gemini-3.6-flash",
    )
    fake_models = FakeModels(outcomes)
    instance = provider_module.GeminiProfileProvider.__new__(
        provider_module.GeminiProfileProvider
    )
    instance.settings = settings
    instance.client = SimpleNamespace(
        models=provider_module._RetryingModelsProxy(fake_models)
    )
    instance._part = lambda data, mime: (data, mime)
    return instance, fake_models


VALID_RESPONSE = "{}"


class GeminiFallbackTests(unittest.TestCase):
    def setUp(self):
        self.sleep = patch.object(provider_module.time, "sleep").start()
        self.addCleanup(patch.stopall)

    def test_primary_success_does_not_call_fallback(self):
        instance, models = make_provider({"gemini-3.7-flash": [VALID_RESPONSE]})

        inference = instance.analyze(b"front", b"back")

        self.assertEqual(models.calls, ["gemini-3.7-flash"])
        self.assertEqual(inference.provider, "gemini-3.7-flash")
        self.assertFalse(inference.fallback_used)

    def test_exhausted_primary_503_uses_fallback(self):
        unavailable = lambda: GeminiError(503, "UNAVAILABLE")
        instance, models = make_provider({
            "gemini-3.7-flash": [unavailable(), unavailable(), unavailable()],
            "gemini-3.6-flash": [VALID_RESPONSE],
        })

        inference = instance.analyze(b"front", b"back")

        self.assertEqual(models.calls.count("gemini-3.7-flash"), 3)
        self.assertEqual(models.calls.count("gemini-3.6-flash"), 1)
        self.assertEqual(inference.provider, "gemini-3.6-flash")
        self.assertTrue(inference.fallback_used)

    def test_daily_quota_429_does_not_call_fallback(self):
        quota = GeminiError(
            429,
            "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
        )
        instance, models = make_provider({"gemini-3.7-flash": [quota]})

        with self.assertRaises(GeminiError):
            instance.analyze(b"front", b"back")

        self.assertEqual(models.calls, ["gemini-3.7-flash"])

    def test_fallback_503_is_propagated_once(self):
        unavailable = lambda: GeminiError(503, "UNAVAILABLE")
        fallback_error = unavailable()
        instance, models = make_provider({
            "gemini-3.7-flash": [unavailable(), unavailable(), unavailable()],
            "gemini-3.6-flash": [fallback_error],
        })

        with self.assertRaises(GeminiError) as raised:
            instance.analyze(b"front", b"back")

        self.assertIs(raised.exception, fallback_error)
        self.assertEqual(models.calls.count("gemini-3.6-flash"), 1)
        self.assertIsNotNone(raised.exception.__cause__)

    def test_fallback_result_is_not_persisted(self):
        self.assertFalse(should_persist_profile_result({"fallback_used": True}))
        self.assertTrue(should_persist_profile_result({"fallback_used": False}))


if __name__ == "__main__":
    unittest.main()
