from __future__ import annotations
import json, re

def extract_json_object(text: str) -> dict:
    text = str(text).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text).strip()
    first, last = text.find("{"), text.rfind("}")
    if first < 0 or last < first:
        raise ValueError("No se encontró un objeto JSON.")
    return json.loads(text[first:last+1])

def safe_int(value):
    if value in {None, "", "null"}:
        return None
    try:
        return int(value)
    except Exception:
        match = re.search(r"-?\d{1,4}", str(value))
        return int(match.group()) if match else None

def normalize_list(value) -> list[str]:
    value = value or []
    if isinstance(value, str):
        value = [value] if value.strip() else []
    return [str(x).strip() for x in value if str(x).strip()]

def clean_type_id(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.split("?")[0].split("#")[0].rstrip("/")
    if "/ocre/id/" in text:
        text = text.split("/ocre/id/")[-1]
    return text.strip()
