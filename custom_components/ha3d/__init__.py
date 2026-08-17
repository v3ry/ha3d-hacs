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
    register_views(hass, models_dir, store)

    # Servir le frontend (index.html + modèles) depuis /ha3d/
    frontend_dir = Path(__file__).resolve().parent / "frontend"
    from homeassistant.components.http import StaticPathConfig
    await hass.http.async_register_static_paths([
        StaticPathConfig("/ha3d", str(frontend_dir), False)
    ])

    # Panel custom dans la sidebar : webcomponent ES6 → custom element <ha3d-panel>
    from homeassistant.components.panel_custom import async_register_panel
    await async_register_panel(
        hass,
        webcomponent_name="ha3d-panel",
        frontend_url_path="ha3d-panel",
        module_url="/ha3d/panel.js",
        sidebar_title="Ha3D",
        sidebar_icon="mdi:home-3d",
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
