import logging
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResultType
import homeassistant.util.voluptuous_serialize as vol
from .const import DOMAIN, DEFAULT_URL

_LOGGER = logging.getLogger(__name__)

class KompasEnergetycznyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Optional("url", default=DEFAULT_URL): str}),
            )
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Kompas Energetyczny", data={"url": user_input["url"]})