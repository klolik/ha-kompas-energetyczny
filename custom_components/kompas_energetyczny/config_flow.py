"""Config Flow for Kompas Energetyczny"""

import logging
from homeassistant import config_entries
from homeassistant.helpers.config_validation import empty_config_schema
import voluptuous as vol
from .const import DOMAIN, API_URL_PRZESYLY

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = empty_config_schema


class KompasEnergetycznyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow for KompasEnergetyczny"""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Optional("url", default=API_URL_PRZESYLY): str}),
            )

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Kompas Energetyczny", data={"url": user_input["url"]})
