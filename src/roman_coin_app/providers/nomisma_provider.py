from __future__ import annotations
import requests
from roman_coin_app.config import Settings

class NomismaProvider:
    QUERY_URL="https://nomisma.org/query"
    FINDSPOTS_URL="https://nomisma.org/apis/getFindspots"
    HOARDS_URL="https://nomisma.org/apis/getHoards"

    def __init__(self, settings: Settings | None=None):
        self.settings=settings or Settings.from_environment()
        self.session=requests.Session()
        self.session.headers.update({"User-Agent":"RomanCoinTFM/1.0 application"})

    def sparql(self, query: str) -> dict:
        r=self.session.get(
            self.QUERY_URL,
            params={"query":query},
            timeout=self.settings.request_timeout,
            headers={"Accept":"application/sparql-results+json"},
        )
        r.raise_for_status()
        return r.json()

    def _geojson(self, endpoint: str, coin_type_uri: str) -> dict:
        r=self.session.get(
            endpoint,
            params={"coinType":coin_type_uri},
            timeout=self.settings.request_timeout,
            headers={"Accept":"application/geo+json"},
        )
        r.raise_for_status()
        return r.json()

    def findspots(self, coin_type_uri: str) -> dict:
        return self._geojson(self.FINDSPOTS_URL,coin_type_uri)

    def hoards(self, coin_type_uri: str) -> dict:
        return self._geojson(self.HOARDS_URL,coin_type_uri)
