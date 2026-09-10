from __future__ import annotations


def should_persist_profile_result(result: dict) -> bool:
    """Keep fallback output session-local so the primary model is retried later."""
    return not bool(result.get("fallback_used", False))
