# Ficha inteligente de moneda romana

Aplicación Streamlit para identificación probabilística y enriquecimiento
contextual de monedas romanas a partir de fotografías de anverso y reverso.

## Modelo

- Gemini 3.7 Flash
- Enfoque profile-first
- El RIC exacto no se presenta como atribución definitiva
- La confianza mostrada es una estimación interna del modelo y no una
  probabilidad calibrada

## Ejecutar localmente

```bash
python -m pip install -r requirements.txt
```

Crear localmente `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "..."
```

Opcional:

```toml
APP_ACCESS_PASSWORD = "..."
```

Después:

```bash
python -m streamlit run streamlit_app.py
```

## Publicar en Streamlit Community Cloud

1. Crear un repositorio GitHub.
2. Subir el contenido de esta carpeta a la raíz.
3. No subir `.streamlit/secrets.toml`.
4. Abrir https://share.streamlit.io
5. Crear una app nueva.
6. Seleccionar repositorio y rama `main`.
7. Entrypoint: `streamlit_app.py`.
8. En Advanced settings:
   - Python: 3.12
   - Secrets:

```toml
GEMINI_API_KEY = "TU_API_KEY_REAL"
APP_ACCESS_PASSWORD = "CONTRASENA_OPCIONAL"
```

9. Deploy.

## Caché

La aplicación utiliza caché local para evitar inferencias repetidas mientras
el runtime siga activo. Streamlit Community Cloud no garantiza que los
archivos locales persistan entre reinicios o reconstrucciones.

## Seguridad

La API key se obtiene exclusivamente de Secrets o variables de entorno.
Nunca debe almacenarse en GitHub.

Si la app es pública y la cuota Gemini es limitada, se recomienda
`APP_ACCESS_PASSWORD`.

## Limitaciones

La identificación es probabilística. El modelo puede equivocarse incluso con
confianza interna alta. Por ello la aplicación no presenta una referencia RIC
exacta como resultado definitivo.
