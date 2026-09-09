from __future__ import annotations

from typing import Any
import math

import pandas as pd


CONFIDENCE_LABELS_ES = {
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
    "unknown": "No disponible",
}


def safe_text(value: Any, fallback: str = "No disponible") -> str:
    if value is None:
        return fallback

    text = str(value).strip()

    return text if text else fallback


def safe_url(value: Any) -> str:
    text = str(value or "").strip()

    if text.startswith(
        (
            "http://",
            "https://",
        )
    ):
        return text

    return ""


def field_value(
    profile: dict,
    key: str,
    fallback: str = "No disponible",
):
    field = (
        profile.get(
            key,
            {}
        )
        or {}
    )

    value = field.get(
        "value"
    )

    if isinstance(
        value,
        dict,
    ):
        return value

    return safe_text(
        value,
        fallback,
    )


def field_confidence(
    profile: dict,
    key: str,
):
    field = (
        profile.get(
            key,
            {}
        )
        or {}
    )

    value = field.get(
        "confidence"
    )

    try:
        value = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    return max(
        0.0,
        min(
            1.0,
            value,
        ),
    )


def field_confidence_label(
    profile: dict,
    key: str,
):
    field = (
        profile.get(
            key,
            {}
        )
        or {}
    )

    raw = str(
        field.get(
            "confidence_label",
            "unknown",
        )
        or "unknown"
    ).lower()

    return CONFIDENCE_LABELS_ES.get(
        raw,
        raw.capitalize(),
    )


def percent_label(value) -> str:
    try:
        value = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return "—"

    return f"{value * 100:.0f} %"


def date_range_label(
    profile: dict,
) -> str:
    value = field_value(
        profile,
        "date_range",
        fallback={},
    )

    if not isinstance(
        value,
        dict,
    ):
        return safe_text(
            value
        )

    date_from = value.get(
        "from"
    )

    date_to = value.get(
        "to"
    )

    if (
        date_from is None
        and date_to is None
    ):
        return "No disponible"

    if (
        date_from is not None
        and date_to is not None
    ):
        if date_from == date_to:
            return f"{date_from} d. C."

        return (
            f"{date_from}–{date_to} d. C."
        )

    if date_from is not None:
        return f"desde {date_from} d. C."

    return f"hasta {date_to} d. C."


def section(
    enrichment: dict,
    key: str,
) -> dict:
    return (
        enrichment.get(
            key,
            {}
        )
        or {}
    )


def section_available(
    enrichment: dict,
    key: str,
) -> bool:
    return (
        section(
            enrichment,
            key,
        ).get(
            "status"
        )
        == "available"
    )


def first_record(
    section_payload: dict,
) -> dict:
    records = (
        section_payload.get(
            "records",
            []
        )
        or []
    )

    if (
        records
        and isinstance(
            records[0],
            dict,
        )
    ):
        return records[0]

    return {}


def museum_payload(
    enrichment: dict,
) -> dict:
    return first_record(
        section(
            enrichment,
            "museum_presence",
        )
    )


def archaeology_payload(
    enrichment: dict,
) -> dict:
    return first_record(
        section(
            enrichment,
            "archaeological_context",
        )
    )


def metrology_payload(
    enrichment: dict,
) -> dict:
    return first_record(
        section(
            enrichment,
            "metrology",
        )
    )


def market_payload(
    enrichment: dict,
) -> dict:
    return first_record(
        section(
            enrichment,
            "market_and_auctions",
        )
    )


def mint_payload(
    enrichment: dict,
) -> dict:
    return first_record(
        section(
            enrichment,
            "mint_context",
        )
    )


def historical_payload(
    enrichment: dict,
) -> dict:
    return first_record(
        section(
            enrichment,
            "authority_context",
        )
    )


def primary_image_url(
    specimen: dict,
) -> str:
    keys = [
        "combined_image",
        "combined_thumbnail",
        "obverse_image",
        "obverse_thumbnail",
        "reverse_image",
        "reverse_thumbnail",
    ]

    for key in keys:
        url = safe_url(
            specimen.get(
                key
            )
        )

        if url:
            return url

    return ""


def specimen_record_url(
    specimen: dict,
) -> str:
    return safe_url(
        specimen.get(
            "object_uri"
        )
    )


def ric_web_url(
    type_id: str,
) -> str:
    type_id = str(
        type_id or ""
    ).strip()

    if not type_id:
        return ""

    return (
        "https://numismatics.org/ocre/id/"
        + type_id
    )


def _first_coordinate_pair(
    value,
):
    if (
        isinstance(
            value,
            (list, tuple),
        )
        and len(value) >= 2
        and all(
            isinstance(
                x,
                (int, float),
            )
            for x in value[:2]
        )
    ):
        lon = float(
            value[0]
        )

        lat = float(
            value[1]
        )

        if (
            math.isfinite(
                lon
            )
            and math.isfinite(
                lat
            )
            and -180 <= lon <= 180
            and -90 <= lat <= 90
        ):
            return lat, lon

    if isinstance(
        value,
        (list, tuple),
    ):
        for item in value:
            found = (
                _first_coordinate_pair(
                    item
                )
            )

            if found:
                return found

    return None


def geo_records_to_dataframe(
    records,
    kind: str,
) -> pd.DataFrame:
    rows = []

    for item in (
        records
        or []
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        pair = (
            _first_coordinate_pair(
                item.get(
                    "coordinates"
                )
            )
        )

        if not pair:
            continue

        lat, lon = pair

        rows.append({
            "lat":
                lat,
            "lon":
                lon,
            "name":
                safe_text(
                    item.get(
                        "name"
                    ),
                    "Sin nombre",
                ),
            "kind":
                kind,
        })

    return pd.DataFrame(
        rows,
        columns=[
            "lat",
            "lon",
            "name",
            "kind",
        ],
    )


def combined_archaeology_map(
    enrichment: dict,
) -> pd.DataFrame:
    payload = archaeology_payload(
        enrichment
    )

    findspots = geo_records_to_dataframe(
        payload.get(
            "findspots",
            []
        ),
        "Hallazgo",
    )

    hoards = geo_records_to_dataframe(
        payload.get(
            "hoards",
            []
        ),
        "Tesoro",
    )

    if findspots.empty:
        return hoards

    if hoards.empty:
        return findspots

    return pd.concat(
        [
            findspots,
            hoards,
        ],
        ignore_index=True,
    )


def mint_map(
    enrichment: dict,
) -> pd.DataFrame:
    payload = mint_payload(
        enrichment
    )

    return geo_records_to_dataframe(
        payload.get(
            "geography",
            []
        ),
        "Ceca",
    )


def compact_sources(
    sources,
):
    out = []
    seen = set()

    for item in (
        sources
        or []
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        name = safe_text(
            item.get(
                "name"
            ),
            "Fuente",
        )

        url = safe_url(
            item.get(
                "url"
            )
        )

        role = safe_text(
            item.get(
                "role"
            ),
            "",
        )

        key = (
            name,
            url,
            role,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        out.append({
            "name":
                name,
            "url":
                url,
            "role":
                role,
        })

    return out
