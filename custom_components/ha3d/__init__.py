"""Intégration Ha3D — visualiseur 3D des capteurs Home Assistant.

Panneau dans la sidebar + API /api/ha3d/* avec authentification native HA.
"""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import CONFIG_DIR, DOMAIN, LAYOUT_FILE
from .http import register_views
from .layout import LayoutStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Optional(CONF_NAME, default="Ha3D"): cv.string})},
    extra=vol.ALLOW_EXTRA,
)

# Panel iframe dans la sidebar HA
PANEL_URL = "/ha3d/index.html"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup YAML legacy (optionnel)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure l'intégration : layout store, vues API, panneau sidebar."""
    config_dir = Path(hass.config.path(CONFIG_DIR))
    store = LayoutStore(config_dir / LAYOUT_FILE)

    models_dir = Path(__file__).resolve().parent / "frontend" / "models"
    if not models_dir.exists():
        _LOGGER.warning("dossier modèles introuvable: %s", models_dir)
        models_dir.mkdir(parents=True, exist_ok=True)

    # Enregistre les vues /api/ha3d/* (auth native HA)
    register_views(hass, models_dir)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["store"] = store
    hass.data[DOMAIN]["models_dir"] = models_dir

    # Servir le frontend (index.html + modèles) depuis /ha3d/
    frontend_dir = Path(__file__).resolve().parent / "frontend"
    hass.http.register_static_path("/ha3d", str(frontend_dir))

    # Panel custom dans la sidebar : module ES6 → custom element <ha3d-panel>
    from homeassistant.components.frontend import add_extra_module_url
    add_extra_module_url(hass, "/ha3d/panel.js")
    await hass.components.frontend.async_register_built_in_panel(
        hass,
        "ha3d-panel",
        "Ha3D",
        "mdi:home-3d",
        require_admin=False,
    )

    _LOGGER.info("Ha3D prêt — %s pièces, %s capteurs, %s portes",
                 len(store.layout.get("levels", [{}])[0].get("rooms", [])),
                 len(store.layout.get("sensors", [])),
                 len(store.layout.get("doors", [])))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l'intégration."""
    return True
