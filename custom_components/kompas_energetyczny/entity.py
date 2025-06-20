"""Entity for Kompas Energetyczny"""

from dataclasses import dataclass
import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import requests

from .const import DOMAIN, API_URL_SZCZYT

_LOGGER = logging.getLogger(__name__)


class KompasEnergetycznyDataUpdateCoordinator(DataUpdateCoordinator):
    """Power data polling coordinator"""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.debug("initializing coordinator: %s", entry)
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=300)
        )
        self.entry = entry
        self.url = entry.data.get("url")
        _LOGGER.debug("url: %s", self.url)
        self.data = None

    async def _async_update_data(self):
        try:
            _LOGGER.debug("calling %s", self.url)
            response = await self.hass.async_add_executor_job(requests.get, self.url)
            response.raise_for_status()
            self.data = response.json()
            _LOGGER.debug("received %s", self.data)
            return self.data
        except requests.exceptions.RequestException as ex:
            raise UpdateFailed(f"Error communicating with API: {ex}") from ex


class KompasEnergetycznyPdgszDataUpdateCoordinator(DataUpdateCoordinator):
    """Peak Hours data polling coordinator"""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.debug("initializing pdgsz coordinator: %s", entry)
        super().__init__(hass, _LOGGER, name=entry.title, update_interval=timedelta(seconds=300))
        self.entry = entry
        self.data = None

    async def _async_update_data(self):
        try:
            today = dt_util.now() #TODO# ensure its Poland time zone aware
            url = API_URL_SZCZYT.format(today.strftime("%Y-%m-%d"))
            _LOGGER.debug("calling pdgsz %s", url)
            response = await self.hass.async_add_executor_job(requests.get, url)
            response.raise_for_status()
            self.data = response.json()
            _LOGGER.debug("received pdgsz %s", self.data)
            return self.data
        except requests.exceptions.RequestException as ex:
            raise UpdateFailed(f"Error communicating with pdgsz API: {ex}") from ex


@dataclass
class KompasEnergetycznyApiData:
    """hass.data DOMAIN entry data"""
    device: DeviceInfo
    coordinator: KompasEnergetycznyDataUpdateCoordinator
    coordinator_pdgsz: KompasEnergetycznyPdgszDataUpdateCoordinator
