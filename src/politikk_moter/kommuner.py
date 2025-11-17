"""Kommune-konfigurasjon og grupperinger for pipeline-kjøringer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class KommuneConfig:
    """Beskriver hvordan en kommune skal skrapes."""

    name: str
    url: str
    type: str
    groups: Sequence[str]

    def as_dict(self) -> dict:
        """Konverter til en muterbar dict som er kompatibel med eksisterende scraping-flyt."""
        return {
            "name": self.name,
            "url": self.url,
            "type": self.type,
        }


# Standard kommuner som ble brukt tidligere. Gruppene gjør det mulig
# å selektere ulike kombinasjoner per Slack-kanal.
KOMMUNE_CONFIGS: List[KommuneConfig] = [
    KommuneConfig(
        name="Sauda kommune",
        url="https://www.sauda.kommune.no/innsyn/politiske-moter/",
        type="acos",
        groups=("core",),
    ),
    KommuneConfig(
        name="Strand kommune",
        url="https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/politiske-moter-og-sakspapirer/politisk-motekalender/",
        type="acos",
        groups=("core",),
    ),
    KommuneConfig(
        name="Suldal kommune",
        url="https://www.suldal.kommune.no/innsyn/politiske-moter/",
        type="acos",
        groups=("core",),
    ),
    KommuneConfig(
        name="Hjelmeland kommune",
        url="https://www.hjelmeland.kommune.no/politikk/moteplan-og-sakspapir/innsyn-moteplan/",
        type="acos",
        groups=("core",),
    ),
    KommuneConfig(
        name="Sirdal kommune",
        url="https://innsynpluss.onacos.no/sirdal/moteoversikt/",
        type="onacos",
        groups=("core", "playwright"),
    ),
    KommuneConfig(
        name="Rogaland fylkeskommune",
        url="https://prod01.elementscloud.no/publikum/971045698/Dmb",
        type="elements",
        groups=("core", "playwright"),
    ),
    KommuneConfig(
        name="Sokndal kommune",
        url="https://www.sokndal.kommune.no/innsyn/moteoversikt/",
        type="acos",
        groups=("core",),
    ),
    KommuneConfig(
        name="Bjerkreim kommune",
        url="https://www.bjerkreim.kommune.no/innsyn/moteplan-og-sakslister/",
        type="acos",
        groups=("core",),
    ),
    KommuneConfig(
        name="Time kommune",
        url="https://www.time.kommune.no/politikk/mote-og-saksdokument/moter-og-saksdokument/",
        type="acos",
        groups=("core", "playwright", "turnus"),
    ),
    KommuneConfig(
        name="Klepp kommune",
        url="https://opengov.360online.com/Meetings/KLEPP",
        type="custom",
        groups=("core", "turnus"),
    ),
    KommuneConfig(
        name="Hå kommune",
        url="https://www.ha.no/politikk-og-samfunnsutvikling/mote-og-sakspapir/",
        type="acos",
        groups=("core", "turnus"),
    ),
    KommuneConfig(
        name="Sola kommune",
        url="https://nyttinnsyn.sola.kommune.no/wfinnsyn.ashx?response=moteplan&",
        type="onacos",
        groups=("core", "playwright", "turnus"),
    ),
    KommuneConfig(
        name="Bymiljøpakken",
        url="https://bymiljopakken.no/moter/",
        type="custom",
        groups=("core",),
    ),
    KommuneConfig(
        name="Eigersund kommune",
        url="https://innsyn.onacos.no/eigersund/mote/wfinnsyn.ashx?response=moteplan&",
        type="onacos",
        groups=("core", "playwright"),
    ),
    KommuneConfig(
        name="Stavanger kommune",
        url="https://stavanger-elm.digdem.no/motekalender",
        type="custom",
        groups=("core", "turnus"),
    ),
    KommuneConfig(
        name="Sandnes kommune",
        url="https://opengov.360online.com/Meetings/SANDNESKOMMUNE",
        type="custom",
        groups=("extended",),
    ),
    # Flere kommuner kan legges til her (f.eks. for utvidet Slack-kanal)
    KommuneConfig(
        name="Randaberg kommune",
        url="https://www.randaberg.kommune.no/innsyn/politikk/",
        type="acos",
        groups=("extended", "turnus"),
    ),
]


def get_kommune_configs(groups: Sequence[str]) -> List[dict]:
    """Returner konfigurasjoner for kommuner som matcher minst én av gruppene."""
    if not groups:
        return [config.as_dict() for config in KOMMUNE_CONFIGS]

    group_set = set(groups)
    selected: List[dict] = []
    for config in KOMMUNE_CONFIGS:
        if group_set.intersection(config.groups):
            selected.append(config.as_dict())
    return selected


def get_default_kommune_configs() -> List[dict]:
    """Tidligere standardliste – brukes som fallback."""
    return get_kommune_configs(["core"])