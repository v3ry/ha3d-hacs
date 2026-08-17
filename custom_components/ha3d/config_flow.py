"""Config flow de l'intégration Ha3D — nom de la maison (optionnel)."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import CONF_ENTRY_TITLE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class Ha3dConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flux de configuration Ha3D."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Le nom de la maison est stocké dans l'entrée ; le layout initial
            # (démo) est créé au setup avec ce nom.
            title = user_input.get("name") or CONF_ENTRY_TITLE
            return self.async_create_entry(title=title, data=user_input)
        schema = vol.Schema({
            vol.Optional("name", default=""): cv.string,
        })
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"hint": ""},
            last_step=False,
        )
