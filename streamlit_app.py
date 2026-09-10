from __future__ import annotations


# STREAMLIT_CLOUD_PORTABLE_BOOTSTRAP
import os
import sys
from pathlib import Path

DEPLOY_ROOT = Path(__file__).resolve().parent
DEPLOY_SRC = DEPLOY_ROOT / "src"

if str(DEPLOY_SRC) not in sys.path:
    sys.path.insert(0, str(DEPLOY_SRC))

os.environ.setdefault(
    "ROMAN_COIN_PROJECT_DIR",
    str(DEPLOY_ROOT),
)

os.environ.setdefault(
    "GEMINI_VISION_MODEL",
    "gemini-3.7-flash",
)

os.environ.setdefault(
    "ROMAN_COIN_GEMINI_MAX_ATTEMPTS",
    "1",
)


from pathlib import Path
import hashlib
import html
import json
import os
import re
import sys
import traceback

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(
    __file__
).resolve().parents[1]

SRC_DIR = (
    PROJECT_DIR / "src"
)

APP_DIR = (
    PROJECT_DIR / "app"
)

if str(
    SRC_DIR
) not in sys.path:
    sys.path.insert(
        0,
        str(
            SRC_DIR
        ),
    )

if str(
    APP_DIR
) not in sys.path:
    sys.path.insert(
        0,
        str(
            APP_DIR
        ),
    )

# Permite que Settings funcione tanto en Colab/Drive
# como al desplegar el repositorio en otro entorno.
os.environ.setdefault(
    "ROMAN_COIN_PROJECT_DIR",
    str(
        PROJECT_DIR
    ),
)

from roman_coin_app.config import get_secret, Settings
from roman_coin_app.profile_factory import (
    build_profile_pipeline,
)
from roman_coin_app.schemas import CoinImages

from ui_helpers import (
    archaeology_payload,
    combined_archaeology_map,
    compact_sources,
    date_range_label,
    field_confidence,
    field_confidence_label,
    field_value,
    historical_payload,
    market_payload,
    metrology_payload,
    mint_map,
    mint_payload,
    museum_payload,
    percent_label,
    primary_image_url,
    ric_web_url,
    safe_text,
    safe_url,
    section,
    specimen_record_url,
)

# NB36_SPANISH_LOCALIZATION
# NB37_PUBLICATION_POLISH
import localization_es as publication_loc_es
from localization_es import (
    archaeology_context_label_es, archaeology_summary_es, display_field_value_es,
    display_value_es, historical_summary_es, localize_dataframe_columns_es,
    localize_numismatic_text_es, localize_role_expression_es,
    localize_source_name_es, localize_source_role_es, mint_definition_es,
)


st.set_page_config(
    page_title=(
        "Ficha de moneda romana"
    ),
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# STREAMLIT_OPTIONAL_ACCESS_GATE
def _deployment_access_gate():
    try:
        configured_password = str(
            st.secrets.get(
                "APP_ACCESS_PASSWORD",
                "",
            )
            or ""
        )
    except Exception:
        configured_password = str(
            os.getenv(
                "APP_ACCESS_PASSWORD",
                "",
            )
            or ""
        )

    if not configured_password:
        return

    if st.session_state.get(
        "_deployment_access_granted",
        False,
    ):
        return

    st.title(
        "🏛️ Ficha inteligente de moneda romana"
    )

    st.info(
        "Esta demostración está protegida para evitar "
        "el consumo no autorizado de la cuota de la API."
    )

    supplied = st.text_input(
        "Contraseña de acceso",
        type="password",
    )

    if st.button(
        "Acceder",
        type="primary",
    ):
        if supplied == configured_password:
            st.session_state[
                "_deployment_access_granted"
            ] = True
            st.rerun()
        else:
            st.error(
                "Contraseña incorrecta."
            )

    st.stop()


_deployment_access_gate()



CUSTOM_CSS = """
<style>
.block-container {
    max-width: 1420px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.hero {
    padding: 1.35rem 1.5rem;
    border: 1px solid rgba(120, 95, 60, 0.25);
    border-radius: 16px;
    background: rgba(160, 125, 75, 0.06);
    margin-bottom: 1rem;
}

.hero-title {
    font-size: 2rem;
    font-weight: 750;
    line-height: 1.15;
    margin-bottom: .35rem;
}

.hero-subtitle {
    opacity: .78;
    font-size: 1rem;
}

.ric-warning {
    border-left: 4px solid #b78334;
    padding: .75rem 1rem;
    background: rgba(183, 131, 52, 0.09);
    border-radius: 8px;
    margin: .5rem 0 1rem 0;
}

.small-muted {
    opacity: .72;
    font-size: .9rem;
}

.source-card {
    padding: .7rem .9rem;
    border: 1px solid rgba(120, 120, 120, .2);
    border-radius: 10px;
    margin-bottom: .55rem;
}

.adaptive-kpi {
    min-height: 92px;
    width: 100%;
}

.adaptive-kpi-label {
    font-size: 0.82rem;
    line-height: 1.2;
    margin-bottom: 0.35rem;
    opacity: 0.82;
}

.adaptive-kpi-value {
    line-height: 1.08;
    font-weight: 400;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
    overflow-wrap: break-word;
    word-break: normal;
    min-height: 2.2em;
}

.adaptive-kpi-value.kpi-xl {
    font-size: 2rem;
}

.adaptive-kpi-value.kpi-lg {
    font-size: 1.72rem;
}

.adaptive-kpi-value.kpi-md {
    font-size: 1.45rem;
}

.adaptive-kpi-value.kpi-sm {
    font-size: 1.20rem;
}
</style>
"""

st.markdown(
    CUSTOM_CSS,
    unsafe_allow_html=True,
)


def kpi_font_class(value) -> str:
    text = str(value or "")
    n = len(text)

    if n <= 10:
        return "kpi-xl"
    if n <= 16:
        return "kpi-lg"
    if n <= 24:
        return "kpi-md"
    return "kpi-sm"


def render_adaptive_kpi(column, label, value):
    display_value = str(value) if value not in (None, "") else "—"

    safe_label = html.escape(str(label))
    safe_value = html.escape(display_value)
    size_class = kpi_font_class(display_value)

    with column:
        st.markdown(
            f"""
            <div class="adaptive-kpi">
                <div class="adaptive-kpi-label">{safe_label}</div>
                <div class="adaptive-kpi-value {size_class}">
                    {safe_value}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def input_fingerprint(
    obverse_bytes: bytes,
    reverse_bytes: bytes,
    enable_related_types: bool,
) -> str:
    h = hashlib.sha256()

    h.update(
        obverse_bytes
    )

    h.update(
        b"::reverse::"
    )

    h.update(
        reverse_bytes
    )

    h.update(
        b"::related::"
        + str(
            bool(
                enable_related_types
            )
        ).encode(
            "utf-8"
        )
    )

    h.update(
        b"::model::"
        + Settings.from_environment().gemini_model.encode(
            "utf-8"
        )
    )

    return h.hexdigest()



def result_cache_path(
    input_hash: str,
) -> Path:
    settings = Settings.from_environment()
    cache_dir = settings.cache_dir / "profile_result_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{input_hash}.json"


def load_cached_result(
    input_hash: str,
):
    path = result_cache_path(input_hash)

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_cached_result(
    input_hash: str,
    result: dict,
):
    path = result_cache_path(input_hash)

    path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return path


def format_number(
    value,
    decimals=2,
    suffix="",
):
    try:
        value = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return "—"

    number = f"{value:.{decimals}f}".replace(".", ",")
    return f"{number}{suffix}"


def render_confidence_field(
    profile: dict,
    key: str,
    label: str,
):
    value = display_field_value_es(
        profile,
        key,
    )

    confidence = (
        field_confidence(
            profile,
            key,
        )
    )

    confidence_label = (
        field_confidence_label(
            profile,
            key,
        )
    )

    st.markdown(
        f"**{label}:** {value}"
    )

    if confidence is not None:
        st.progress(
            confidence,
            text=(
                f"{confidence_label} · "
                f"{percent_label(confidence)}"
            ),
        )
    else:
        st.caption(
            "Confianza no disponible"
        )


def render_museum_specimen(
    specimen: dict,
    index: int,
):
    collection = safe_text(
        specimen.get(
            "collection"
        )
        or specimen.get(
            "collection_uri"
        ),
        "Colección no indicada",
    )

    identifier = safe_text(
        specimen.get(
            "identifier"
        ),
        "Sin identificador",
    )

    image_url = (
        primary_image_url(
            specimen
        )
    )

    record_url = (
        specimen_record_url(
            specimen
        )
    )

    title = (
        f"{index}. {collection} · "
        f"{identifier}"
    )

    with st.expander(
        title,
        expanded=(
            index <= 3
        ),
    ):
        left, right = st.columns(
            [1, 1.35]
        )

        with left:
            if image_url:
                try:
                    st.image(
                        image_url,
                        width="stretch",
                    )
                except Exception:
                    st.caption(
                        "La imagen remota no pudo mostrarse."
                    )
            else:
                st.caption(
                    "Sin imagen enlazada."
                )

        with right:
            c1, c2, c3 = st.columns(
                3
            )

            c1.metric(
                "Peso",
                (
                    safe_text(
                        specimen.get(
                            "weight_g"
                        ),
                        "—",
                    )
                    + (
                        " g"
                        if specimen.get(
                            "weight_g"
                        )
                        else ""
                    )
                ),
            )

            c2.metric(
                "Diámetro",
                (
                    safe_text(
                        specimen.get(
                            "diameter_mm"
                        ),
                        "—",
                    )
                    + (
                        " mm"
                        if specimen.get(
                            "diameter_mm"
                        )
                        else ""
                    )
                ),
            )

            c3.metric(
                "Eje",
                safe_text(
                    specimen.get(
                        "axis"
                    ),
                    "—",
                ),
            )

            roles = (
                specimen.get(
                    "match_roles",
                    []
                )
                or []
            )

            if roles:
                st.caption(
                    "Comparabilidad: "
                    + localize_role_expression_es(" + ".join(roles))
                )

            if record_url:
                st.markdown(
                    f"[Abrir registro original]({record_url})"
                )


def render_sources(
    sources,
):
    sources = compact_sources(
        sources
    )

    if not sources:
        st.info(
            "No hay fuentes externas registradas."
        )
        return

    for item in sources:
        name = localize_source_name_es(item["name"])

        role = localize_source_role_es(item.get("role"))

        url = item.get(
            "url"
        )

        if url:
            content = (
                f"**[{name}]({url})**"
            )
        else:
            content = (
                f"**{name}**"
            )

        if role:
            content += (
                f"  \n{role}"
            )

        st.markdown(
            content
        )


# ------------------------------------------------------------
# CABECERA
# ------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="hero-title">🏛️ Ficha inteligente de moneda romana</div>
      <div class="hero-subtitle">
        Sube fotografías del anverso y reverso de la misma moneda.
        El sistema construirá una ficha numismática e histórica enriquecida.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:
    # MANUAL_GEMINI_37_MODEL_BADGE
    settings_ui = Settings.from_environment()

    st.caption(
        "Modelo multimodal: "
        + settings_ui.gemini_model
    )

    st.caption(
        "Modo de prueba: 1 intento por análisis"
    )
    st.header(
        "Configuración"
    )

    gemini_key = get_secret(
        "GEMINI_API_KEY"
    )

    if gemini_key:
        st.success(
            "Gemini API configurada",
            icon="✅",
        )
    else:
        st.warning(
            "Falta GEMINI_API_KEY",
            icon="⚠️",
        )

    force_reanalysis = st.toggle(
        label="Forzar nuevo análisis",
        value=False,
        help=(
            "Desactivado: el mismo par de imágenes reutiliza la ficha guardada. "
            "Activado: solicita una nueva predicción a Gemini."
        ),
    )

    enable_related_types = st.toggle(
        "Mostrar referencias RIC relacionadas",
        value=False,
        help=(
            "Función experimental. "
            "No afecta a la ficha principal."
        ),
    )

    st.caption(
        "El RIC exacto no se considera "
        "identificado salvo evidencia "
        "tipológica suficiente."
    )

    st.divider()

    st.markdown(
        "**Fuentes de enriquecimiento**"
    )

    st.caption(
        "Nomisma · OCRE · Wikidata · "
        "Wikipedia · colecciones enlazadas · "
        "ANS."
    )

    if st.button(
        "Limpiar resultado",
        width="stretch",
    ):
        st.session_state.pop(
            "latest_result",
            None,
        )

        st.session_state.pop(
            "latest_input_hash",
            None,
        )


# ------------------------------------------------------------
# UPLOAD
# ------------------------------------------------------------
left_upload, right_upload = (
    st.columns(
        2,
        gap="large",
    )
)

with left_upload:
    obverse = st.file_uploader(
        "Anverso",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
        key="obverse_upload",
        help=(
            "Fotografía frontal del anverso. "
            "Preferiblemente moneda centrada "
            "y fondo neutro."
        ),
    )

    if obverse:
        st.image(
            obverse,
            caption="Anverso",
            width="stretch",
        )

with right_upload:
    reverse = st.file_uploader(
        "Reverso",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
        key="reverse_upload",
        help=(
            "Fotografía frontal del reverso "
            "de la misma moneda."
        ),
    )

    if reverse:
        st.image(
            reverse,
            caption="Reverso",
            width="stretch",
        )


ready = (
    obverse is not None
    and reverse is not None
)

current_hash = None

if ready:
    current_hash = (
        input_fingerprint(
            obverse.getvalue(),
            reverse.getvalue(),
            enable_related_types,
        )
    )

    stored_hash = (
        st.session_state.get(
            "latest_input_hash"
        )
    )

    if (
        stored_hash
        and stored_hash
        != current_hash
    ):
        st.info(
            "Las imágenes o la configuración han cambiado. "
            "Pulsa «Analizar moneda» para actualizar la ficha."
        )


# ------------------------------------------------------------
# RUN PIPELINE
# ------------------------------------------------------------
analyze_clicked = st.button(
    "Analizar moneda",
    type="primary",
    disabled=not ready,
    width="stretch",
)

if analyze_clicked:
    if not gemini_key:
        st.error(
            "No se puede ejecutar el análisis "
            "porque GEMINI_API_KEY no está configurada."
        )

    else:
        try:
            images = CoinImages(
                obverse_bytes=
                    obverse.getvalue(),
                reverse_bytes=
                    reverse.getvalue(),
                obverse_mime=(
                    obverse.type
                    or "image/jpeg"
                ),
                reverse_mime=(
                    reverse.type
                    or "image/jpeg"
                ),
            )

            cached_result = (
                None
                if force_reanalysis
                else load_cached_result(
                    current_hash
                )
            )

            if cached_result is not None:
                result = cached_result
                st.info(
                    "Se ha reutilizado la ficha guardada "
                    "para estas imágenes."
                )

            else:
                with st.spinner(
                    "Analizando la moneda y construyendo "
                    "la ficha enriquecida..."
                ):
                    pipeline = (
                        build_profile_pipeline(
                            enable_related_types=
                                enable_related_types,
                            max_related_types=5,
                        )
                    )

                    result_obj = pipeline.run(
                        images
                    )

                    result = (
                        result_obj.to_dict()
                    )

                save_cached_result(
                    current_hash,
                    result,
                )

            st.session_state[
                "latest_result"
            ] = result

            st.session_state[
                "latest_input_hash"
            ] = current_hash

            st.success(
                "Ficha generada correctamente.",
                icon="✅",
            )

        except Exception as exc:
            # MANUAL_GEMINI_37_ERROR_MESSAGES
            error_text = f"{type(exc).__name__}: {exc}"
            error_lower = error_text.lower()
            compact_error = re.sub(
                r"[^a-z0-9]+",
                "",
                error_lower,
            )

            if (
                "generaterequestsperdayperprojectpermodelfreetier"
                in compact_error
                or
                "generaterequestsperdayperprojectpermodel"
                in compact_error
            ):
                st.error(
                    "Cuota diaria gratuita de Gemini 3.7 Flash agotada. "
                    "No se realizará un reintento automático."
                )

            elif (
                "503" in error_text
                or
                "unavailable" in error_lower
            ):
                st.warning(
                    "Gemini 3.7 Flash está temporalmente saturado "
                    "o no disponible (503). No se realizará un "
                    "reintento automático."
                )

            elif (
                "429" in error_text
                or
                "resource_exhausted" in error_lower
            ):
                st.warning(
                    "La API de Gemini ha alcanzado un límite "
                    "de cuota o frecuencia (429). No se realizará "
                    "un reintento automático."
                )

            else:
                st.error(
                    "No se pudo completar el análisis."
                )

            with st.expander(
                "Detalle técnico del error"
            ):
                st.code(
                    "".join(
                        traceback.format_exception(
                            type(exc),
                            exc,
                            exc.__traceback__,
                        )
                    )
                )


result = st.session_state.get(
    "latest_result"
)

if not result:
    st.info(
        "Sube anverso y reverso para generar una ficha."
    )

    st.stop()


# ------------------------------------------------------------
# PREPARE RESULT
# ------------------------------------------------------------
profile = (
    result.get(
        "profile",
        {}
    )
    or {}
)

enrichment = (
    result.get(
        "enrichment",
        {}
    )
    or {}
)

warnings = (
    result.get(
        "warnings",
        []
    )
    or []
)

errors = (
    result.get(
        "errors",
        []
    )
    or []
)


# ------------------------------------------------------------
# PRIMARY IDENTIFICATION
# ------------------------------------------------------------
st.divider()

authority = display_field_value_es(
    profile,
    "authority",
)

denomination = display_field_value_es(
    profile,
    "denomination",
)

material = display_field_value_es(
    profile,
    "material",
)

mint = display_field_value_es(
    profile,
    "mint",
)

date_label = (
    date_range_label(
        profile
    )
)

overall_conf = (
    profile.get(
        "overall_confidence"
    )
)

overall_label = safe_text(
    profile.get(
        "overall_confidence_label"
    ),
    "unknown",
)

overall_label_es = {
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
    "unknown": "No disponible",
}.get(
    overall_label.lower(),
    overall_label,
)

st.subheader(
    "Identificación probable"
)

main_cols = st.columns(
    6
)

render_adaptive_kpi(
    main_cols[0],
    "Autoridad",
    authority,
)

render_adaptive_kpi(
    main_cols[1],
    "Denominación",
    denomination,
)

render_adaptive_kpi(
    main_cols[2],
    "Material",
    material,
)

render_adaptive_kpi(
    main_cols[3],
    "Ceca",
    mint,
)

render_adaptive_kpi(
    main_cols[4],
    "Cronología",
    date_label,
)

confidence_value = (
    f"{overall_label_es}"
    + (
        f" · {percent_label(overall_conf)}"
        if overall_conf is not None
        else ""
    )
)

render_adaptive_kpi(
    main_cols[5],
    "Confianza interna",
    confidence_value,
)

st.caption(
    "La confianza es una estimación interna del modelo y no equivale a una probabilidad calibrada de acierto."
)

if result.get(
    "exact_ric_type_id"
):
    st.warning(
        "Existe una referencia RIC asignada, "
        "pero debe interpretarse según la política "
        "de confianza tipológica del sistema."
    )
else:
    st.markdown(
        """
        <div class="ric-warning">
        <strong>Referencia tipológica:</strong>
        el RIC exacto no se determina de forma concluyente.
        La ficha se construye a partir de los atributos numismáticos
        identificados y de fuentes externas relacionadas.
        </div>
        """,
        unsafe_allow_html=True,
    )


if warnings:
    with st.expander(
        f"Avisos del pipeline ({len(warnings)})"
    ):
        for item in warnings:
            st.warning(
                str(item)
            )

if errors:
    with st.expander(
        f"Errores registrados ({len(errors)})"
    ):
        for item in errors:
            st.error(
                str(item)
            )


tabs = st.tabs([
    "🔎 Identificación",
    "🏺 Historia y ceca",
    "🏛️ Museos",
    "🗺️ Hallazgos",
    "⚖️ Metrología y procedencia",
    "📚 Fuentes y JSON",
])


# ------------------------------------------------------------
# TAB 1 — IDENTIFICATION
# ------------------------------------------------------------
with tabs[0]:
    st.subheader(
        "Confianza interna por atributo"
    )

    c1, c2 = st.columns(
        2,
        gap="large",
    )

    with c1:
        render_confidence_field(
            profile,
            "authority",
            "Autoridad",
        )

        render_confidence_field(
            profile,
            "denomination",
            "Denominación",
        )

        render_confidence_field(
            profile,
            "material",
            "Material",
        )

        render_confidence_field(
            profile,
            "mint",
            "Ceca",
        )

    with c2:
        render_confidence_field(
            profile,
            "dynasty",
            "Dinastía",
        )

        render_confidence_field(
            profile,
            "period",
            "Periodo",
        )

        render_confidence_field(
            profile,
            "date_range",
            "Cronología",
        )

    st.divider()

    st.subheader(
        "Observación visual"
    )

    evidence = (
        profile.get(
            "evidence",
            {}
        )
        or {}
    )

    obv, rev = st.columns(
        2,
        gap="large",
    )

    with obv:
        st.markdown(
            "#### Anverso"
        )

        fragments = (
            evidence.get(
                "visible_obverse_fragments",
                []
            )
            or []
        )

        if fragments:
            st.write(
                "**Fragmentos visibles:** "
                + " · ".join(
                    fragments
                )
            )

        st.write(
            "**Busto observado:**",
            localize_numismatic_text_es(safe_text(evidence.get("observed_bust")), context="bust"),
        )

        st.write(
            "**Leyenda reconstruida:**",
            field_value(
                profile,
                "obverse_legend",
            ),
        )

        st.write(localize_numismatic_text_es(safe_text(profile.get("obverse_description")), context="description"))

    with rev:
        st.markdown(
            "#### Reverso"
        )

        fragments = (
            evidence.get(
                "visible_reverse_fragments",
                []
            )
            or []
        )

        if fragments:
            st.write(
                "**Fragmentos visibles:** "
                + " · ".join(
                    fragments
                )
            )

        st.write(
            "**Iconografía observada:**",
            localize_numismatic_text_es(safe_text(evidence.get("observed_reverse_iconography")), context="iconography"),
        )

        st.write(
            "**Exergo / marca:**",
            localize_numismatic_text_es(safe_text(evidence.get("exergue_or_mintmark")), context="exergue"),
        )

        st.write(
            "**Leyenda reconstruida:**",
            field_value(
                profile,
                "reverse_legend",
            ),
        )

        st.write(localize_numismatic_text_es(safe_text(profile.get("reverse_description")), context="description"))

    uncertainties = (
        profile.get(
            "uncertainties",
            []
        )
        or []
    )

    if uncertainties:
        st.subheader(
            "Incertidumbres"
        )

        for item in uncertainties:
            st.write("•", localize_numismatic_text_es(item, context="uncertainty"))

    related = (
        result.get(
            "related_types",
            []
        )
        or []
    )

    if related:
        st.divider()

        st.subheader(
            "Referencias RIC relacionadas"
        )

        st.warning(
            "Estas referencias son candidatas compatibles "
            "o relacionadas. No constituyen una "
            "identificación RIC definitiva."
        )

        for item in related:
            type_id = safe_text(
                item.get(
                    "type_id"
                ),
                "",
            )

            url = ric_web_url(
                type_id
            )

            label = (
                f"[{type_id}]({url})"
                if url
                else type_id
            )

            rank = item.get(
                "rank"
            )

            local_rank = item.get(
                "local_rank"
            )

            api_rank = item.get(
                "api_rank"
            )

            detail = []

            if rank is not None:
                detail.append(
                    f"híbrido #{rank}"
                )

            if local_rank is not None:
                detail.append(
                    f"local #{local_rank}"
                )

            if api_rank is not None:
                detail.append(
                    f"API #{api_rank}"
                )

            st.markdown(
                f"- **{label}**"
                + (
                    " — "
                    + ", ".join(
                        detail
                    )
                    if detail
                    else ""
                )
            )


# ------------------------------------------------------------
# TAB 2 — HISTORY + MINT
# ------------------------------------------------------------
with tabs[1]:
    authority_section = section(
        enrichment,
        "authority_context",
    )

    st.subheader(
        "Contexto histórico"
    )

    hist = historical_payload(
        enrichment
    )
    historical_summary = historical_summary_es(authority_section, hist, profile)
    st.write(historical_summary)

    wikipedia = (
        hist.get(
            "wikipedia_es",
            {}
        )
        or {}
    )

    wikidata = (
        hist.get(
            "wikidata",
            {}
        )
        or {}
    )

    nomisma = (
        hist.get(
            "nomisma",
            {}
        )
        or {}
    )

    source_cols = st.columns(
        3
    )

    if safe_url(
        nomisma.get(
            "uri"
        )
    ):
        source_cols[0].markdown(
            f"[Nomisma: {display_value_es(safe_text(nomisma.get('label'), authority), 'authority')}]"
            f"({nomisma['uri']})"
        )

    if safe_url(
        wikidata.get(
            "entity_url"
        )
    ):
        source_cols[1].markdown(
            f"[Wikidata: {safe_text(wikidata.get('qid'), '')}]"
            f"({wikidata['entity_url']})"
        )

    if safe_url(
        wikipedia.get(
            "url"
        )
    ):
        source_cols[2].markdown(
            f"[Wikipedia ES]({wikipedia['url']})"
        )

    st.divider()

    st.subheader(
        "Ceca"
    )

    mint_section = section(
        enrichment,
        "mint_context",
    )

    mint_data = mint_payload(
        enrichment
    )
    st.write(mint_definition_es(mint_data.get("definition"), mint_data.get("label") or mint))

    if mint_data:
        st.caption(
            (
                "Concepto Nomisma: "
                + safe_text(
                    mint_data.get(
                        "label"
                    ),
                    mint,
                )
            )
        )

    mint_df = mint_map(
        enrichment
    )

    if not mint_df.empty:
        st.map(
            mint_df,
            latitude="lat",
            longitude="lon",
            height=360,
        )


# ------------------------------------------------------------
# TAB 3 — MUSEUMS
# ------------------------------------------------------------
with tabs[2]:
    museum_section = section(
        enrichment,
        "museum_presence",
    )

    st.subheader(
        "Museos y ejemplares comparables"
    )

    st.write(
        safe_text(
            museum_section.get(
                "summary"
            )
        )
    )

    museum = museum_payload(
        enrichment
    )

    collections = (
        museum.get(
            "collections",
            []
        )
        or []
    )

    specimens = (
        museum.get(
            "specimens",
            []
        )
        or []
    )

    query_strategy = (
        museum.get(
            "query_strategy",
            []
        )
        or []
    )

    museum_counts = publication_loc_es.museum_display_counts_es(
        museum
    )

    m1, m2, m3 = st.columns(
        3
    )

    m1.metric(
        "Ejemplares localizados",
        museum_counts["located"],
    )

    m2.metric(
        "Ejemplares en ficha",
        museum_counts["in_payload"],
    )

    m3.metric(
        "Colecciones",
        museum_counts["collections"],
    )

    if query_strategy:
        st.caption(
            "Criterio de comparación: " + localize_role_expression_es(" + ".join(query_strategy))
        )

    if collections:
        st.markdown(
            "#### Colecciones"
        )

        st.dataframe(
            localize_dataframe_columns_es(pd.DataFrame(collections)),
            hide_index=True,
            width="stretch",
        )

    if specimens:
        st.markdown(
            "#### Ejemplares"
        )

        for idx, specimen in enumerate(
            specimens[:12],
            start=1,
        ):
            render_museum_specimen(
                specimen,
                idx,
            )

        if len(specimens) > 12:
            st.caption(
                f"Se muestran {museum_counts['shown']} de "
                f"{museum_counts['in_payload']} ejemplares conservados "
                "en la ficha. El total de ejemplares localizados puede "
                "ser mayor porque la ficha limita los registros detallados."
            )
    else:
        st.info(
            "No se recuperaron ejemplares comparables "
            "en las fuentes enlazadas."
        )


# ------------------------------------------------------------
# TAB 4 — FINDS + HOARDS
# ------------------------------------------------------------
with tabs[3]:
    arch_section = section(
        enrichment,
        "archaeological_context",
    )

    st.subheader(
        "Hallazgos y tesoros"
    )

    arch = archaeology_payload(
        enrichment
    )
    st.write(archaeology_summary_es(arch))

    findspots = (
        arch.get(
            "findspots",
            []
        )
        or []
    )

    hoards = (
        arch.get(
            "hoards",
            []
        )
        or []
    )

    a1, a2 = st.columns(
        2
    )

    a1.metric(
        "Hallazgos recuperados",
        len(
            findspots
        ),
    )

    a2.metric(
        "Tesoros recuperados",
        len(
            hoards
        ),
    )

    context_role = safe_text(
        arch.get(
            "context_role"
        ),
        "",
    )

    context_id = safe_text(
        arch.get(
            "context_nomisma_id"
        ),
        "",
    )

    if context_role or context_id:
        context_label = archaeology_context_label_es(context_role, context_id, profile)
        st.caption("Contexto de distribución: " f"{context_label}. No representa el RIC exacto.")

    arch_map = (
        combined_archaeology_map(
            enrichment
        )
    )

    if not arch_map.empty:
        st.map(
            arch_map,
            latitude="lat",
            longitude="lon",
            height=500,
        )

        with st.expander(
            "Ver puntos recuperados"
        ):
            st.dataframe(
                arch_map,
                hide_index=True,
                width="stretch",
            )

    else:
        st.info(
            "No hay coordenadas geográficas "
            "disponibles para mostrar."
        )


# ------------------------------------------------------------
# TAB 5 — METROLOGY + PROVENANCE
# ------------------------------------------------------------
with tabs[4]:
    st.subheader(
        "Metrología comparativa"
    )

    metrology_section = section(
        enrichment,
        "metrology",
    )

    st.write(
        safe_text(
            metrology_section.get(
                "summary"
            )
        )
    )

    metro = metrology_payload(
        enrichment
    )

    nomisma_api = (
        metro.get(
            "nomisma_api",
            {}
        )
        or {}
    )

    specimen_stats = (
        metro.get(
            "retrieved_specimen_stats",
            {}
        )
        or {}
    )

    display_weight = publication_loc_es.preferred_metrology_value_es(
        nomisma_api, specimen_stats, "average_weight_g", "weight_g"
    )
    display_diameter = publication_loc_es.preferred_metrology_value_es(
        nomisma_api, specimen_stats, "average_diameter_mm", "diameter_mm"
    )
    display_axis = publication_loc_es.preferred_metrology_value_es(
        nomisma_api, specimen_stats, "average_axis", "axis"
    )

    mc1, mc2, mc3 = st.columns(
        3
    )

    mc1.metric(
        "Peso medio",
        format_number(
            display_weight,
            2,
            " g",
        ),
    )

    mc2.metric(
        "Diámetro medio",
        format_number(
            display_diameter,
            2,
            " mm",
        ),
    )

    mc3.metric(
        "Eje medio",
        format_number(
            display_axis,
            2,
            " h",
        ),
    )

    if specimen_stats:
        rows = []

        labels = {
            "weight_g":
                "Peso (g)",
            "diameter_mm":
                "Diámetro (mm)",
            "axis":
                "Eje (h)",
        }

        for key, stats in specimen_stats.items():
            stats = (
                stats
                or {}
            )

            rows.append({
                "Variable":
                    labels.get(
                        key,
                        key,
                    ),
                "n":
                    stats.get(
                        "n"
                    ),
                "Media":
                    stats.get(
                        "mean"
                    ),
                "Mínimo":
                    stats.get(
                        "min"
                    ),
                "Máximo":
                    stats.get(
                        "max"
                    ),
            })

        st.dataframe(
            pd.DataFrame(
                rows
            ),
            hide_index=True,
            width="stretch",
        )

    filters = (
        nomisma_api.get(
            "filters",
            []
        )
        or []
    )

    if filters:
        st.caption(
            "Restricciones metrológicas: " + localize_role_expression_es(" + ".join(filters))
        )

    st.divider()

    st.subheader(
        "Procedencia y menciones de subasta"
    )

    market_section = section(
        enrichment,
        "market_and_auctions",
    )

    st.write(
        safe_text(
            market_section.get(
                "summary"
            )
        )
    )

    market = market_payload(
        enrichment
    )

    provenance = (
        market.get(
            "ans_provenance",
            []
        )
        or []
    )

    auction_mentions = (
        market.get(
            "auction_mentions",
            []
        )
        or []
    )

    p1, p2 = st.columns(
        2
    )

    p1.metric(
        "Registros ANS revisados",
        len(
            provenance
        ),
    )

    p2.metric(
        "Menciones venta/subasta",
        len(
            auction_mentions
        ),
    )

    if provenance:
        with st.expander(
            "Procedencia ANS publicada"
        ):
            for item in provenance:
                identifier = safe_text(
                    item.get(
                        "identifier"
                    ),
                    "Registro ANS",
                )

                url = safe_url(
                    item.get(
                        "record_url"
                    )
                )

                if url:
                    st.markdown(
                        f"**[{identifier}]({url})**"
                    )
                else:
                    st.markdown(
                        f"**{identifier}**"
                    )

                sections = (
                    item.get(
                        "provenance_sections",
                        []
                    )
                    or []
                )

                for sec in sections:
                    st.write(
                        "•",
                        safe_text(
                            sec.get(
                                "text"
                            )
                        ),
                    )

    if auction_mentions:
        with st.expander(
            "Menciones abiertas de subasta"
        ):
            st.dataframe(
                localize_dataframe_columns_es(pd.DataFrame(auction_mentions)),
                hide_index=True,
                width="stretch",
            )


# ------------------------------------------------------------
# TAB 6 — SOURCES + JSON
# ------------------------------------------------------------
with tabs[5]:
    st.subheader(
        "Fuentes"
    )

    render_sources(
        enrichment.get(
            "sources",
            []
        )
    )

    st.caption(
        "La disponibilidad de museos, hallazgos, "
        "tesoros y procedencias depende de los "
        "datasets abiertos enlazados consultados; "
        "no constituye un censo exhaustivo."
    )

    st.divider()

    st.subheader(
        "Resultado técnico"
    )
    st.caption("Las claves del JSON conservan sus nombres técnicos originales para mantener la compatibilidad del contrato de datos; la interfaz visible está localizada al español.")

    result_json = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    st.download_button(
        "Descargar ficha JSON",
        data=result_json,
        file_name="roman_coin_profile.json",
        mime="application/json",
        width="stretch",
    )

    with st.expander(
        "Ver JSON completo"
    ):
        st.json(
            result,
            expanded=2,
        )
