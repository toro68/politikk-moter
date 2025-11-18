"""Ensure kommune-konfigurasjonene holder forventet struktur."""

from __future__ import annotations

import pytest

from politikk_moter.kommuner import KOMMUNE_CONFIGS, get_kommune_configs  # pylint: disable=import-error


EXPECTED_KOMMUNER = {
    "Sauda kommune": {"type": "acos", "groups": {"core"}},
    "Strand kommune": {"type": "acos", "groups": {"core"}},
    "Suldal kommune": {"type": "acos", "groups": {"core"}},
    "Hjelmeland kommune": {"type": "acos", "groups": {"core"}},
    "Sirdal kommune": {"type": "onacos", "groups": {"core", "playwright"}},
    "Rogaland fylkeskommune": {"type": "elements", "groups": {"core", "playwright"}},
    "Sokndal kommune": {"type": "acos", "groups": {"core"}},
    "Bjerkreim kommune": {"type": "acos", "groups": {"core"}},
    "Time kommune": {"type": "acos", "groups": {"core", "playwright", "turnus"}},
    "Klepp kommune": {"type": "custom", "groups": {"core", "turnus"}},
    "Hå kommune": {"type": "acos", "groups": {"core", "turnus"}},
    "Sola kommune": {"type": "onacos", "groups": {"core", "playwright", "turnus"}},
    "Bymiljøpakken": {"type": "custom", "groups": {"core"}},
    "Eigersund kommune": {"type": "onacos", "groups": {"core", "playwright"}},
    "Sandnes kommune": {"type": "custom", "groups": {"extended"}},
    "Randaberg kommune": {"type": "acos", "groups": {"extended", "turnus"}},
    "Stavanger kommune": {"type": "custom", "groups": {"core", "turnus"}},
}


@pytest.mark.parametrize("name", sorted(EXPECTED_KOMMUNER))
def test_kommune_config_present(name: str) -> None:
    config = next((cfg for cfg in KOMMUNE_CONFIGS if cfg.name == name), None)
    assert config is not None, f"Manglende konfig for {name}"
    assert config.url, f"{name} må ha URL"
    assert config.type == EXPECTED_KOMMUNER[name]["type"]
    assert set(config.groups) == EXPECTED_KOMMUNER[name]["groups"]


def test_kommune_names_are_unique() -> None:
    names = [cfg.name for cfg in KOMMUNE_CONFIGS]
    assert len(names) == len(set(names)), "Kommunenavn må være unike"


def test_get_kommune_configs_respects_groups() -> None:
    extended = get_kommune_configs(["extended"])
    extended_names = {cfg["name"] for cfg in extended}
    assert extended_names == {"Sandnes kommune", "Randaberg kommune"}

    core = get_kommune_configs(["core"])
    core_names = {cfg["name"] for cfg in core}
    assert "Sandnes kommune" not in core_names
    assert "Sauda kommune" in core_names

    turnus = get_kommune_configs(["turnus"])
    turnus_names = {cfg["name"] for cfg in turnus}
    assert turnus_names == {
        "Hå kommune",
        "Klepp kommune",
        "Randaberg kommune",
        "Sola kommune",
        "Stavanger kommune",
        "Time kommune",
    }
