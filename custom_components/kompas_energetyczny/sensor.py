import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
import requests
from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    _LOGGER.info("setting up coordinator for %s", entry)
    coordinator = KompasEnergetycznyDataUpdateCoordinator(hass, entry)
    _LOGGER.info("awaiting coordinator first refresh %s", entry)
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("assigning coordinator %s", entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    _LOGGER.info("setting up sensors")
    sensors = [
        {"key": "wodne", "name": "wodne", "device_class": None},
        {"key": "wiatrowe", "name": "wiatrowe", "device_class": None},
        {"key": "PV", "name": "PV", "device_class": None},
        {"key": "generacja", "name": "generacja", "device_class": None},
        {"key": "zapotrzebowanie", "name": "zapotrzebowanie", "device_class": None},
        {"key": "cieplne", "name": "cieplne", "device_class": None},
#        {"key": "timestamp", "name": "Timestamp", "device_class": "timestamp"},
    ]
    entities = [ KompasEnergetycznySensor(coordinator, sensor_config) for sensor_config in sensors ]

    async_add_entities(entities)
    return True

class KompasEnergetycznyDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.info("initializing coordinator: %s", entry)
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=300)
        )
        self.entry = entry
        self.url = entry.data.get("url")
        _LOGGER.info("url: %s", self.url)
        self.data = None

    async def _async_update_data(self):
        try:
            _LOGGER.info("calling %s", self.url)
            response = await self.hass.async_add_executor_job(requests.get, self.url)
            response.raise_for_status()
            self.data = response.json()
            _LOGGER.info("received %s", self.data)
            return self.data
        except requests.exceptions.RequestException as ex:
            raise UpdateFailed(f"Error communicating with API: {ex}") from ex

class KompasEnergetycznySensor(SensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, sensor_config: dict) -> None:
        super().__init__()
        _LOGGER.info("setting up %s", sensor_config)
        self._coordinator = coordinator
        self._sensor_key = sensor_config["key"]
        self._attr_name = f"{DEFAULT_NAME} {sensor_config['name']}"
        self._attr_unique_id = f"{self._coordinator.entry.entry_id}_{self._sensor_key}"
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_unit_of_measurement = sensor_config.get("unit")

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def native_value(self):
        podsumowanie = self._coordinator.data.get("data", {}).get("podsumowanie", {})
        if self._sensor_key in podsumowanie:
            value = podsumowanie[self._sensor_key]
#            if self._sensor_key == "timestamp":
#                return dt_util.parse_datetime(value)
            return value
        return None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )
