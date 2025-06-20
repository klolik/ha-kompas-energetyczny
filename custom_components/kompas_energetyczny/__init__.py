"""The Kompas Energetyczny component."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN, MANUFACTURER, DEFAULT_NAME, HOME_URL, PRECISION, STATUS_MAP
from .entity import KompasEnergetycznyDataUpdateCoordinator, KompasEnergetycznyPdgszDataUpdateCoordinator, KompasEnergetycznyApiData


PLATFORMS = [Platform.SENSOR]


_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Setup integration"""
    if DOMAIN not in hass.data:
        hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup config entry"""

    _LOGGER.debug("setting up coordinator for %s", entry)
    coordinator = KompasEnergetycznyDataUpdateCoordinator(hass, entry)
    _LOGGER.debug("awaiting coordinator first refresh %s", entry)
    await coordinator.async_config_entry_first_refresh()

    _LOGGER.debug("setting up pdgsz coordinator for %s", entry)
    coordinator_pdgsz = KompasEnergetycznyPdgszDataUpdateCoordinator(hass, entry)
    _LOGGER.debug("awaiting pdgsz coordinator first refresh %s", entry)
    await coordinator_pdgsz.async_config_entry_first_refresh()

    device = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, DOMAIN)},
        manufacturer=MANUFACTURER,
        name=DEFAULT_NAME,
        configuration_url=HOME_URL,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = KompasEnergetycznyApiData(device, coordinator, coordinator_pdgsz)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry"""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return True
