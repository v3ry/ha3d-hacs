"""Config flow de l'intégration Ha3D — aucune configuration requise."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DOMAIN_TITLE

_LOGGER = logging.getLogger(__name__)

SCHEMA = vol.Schema({})


async def validate_input(hass: HomeAssistant) -> None:
    """Vérifie que l'intégration est prête (rien à valider)."""
    return None


class Ha3dConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flux de configuration Ha3D."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=DOMAIN_TITLE, data={})
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
