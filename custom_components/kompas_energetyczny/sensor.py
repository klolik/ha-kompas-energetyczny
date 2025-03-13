import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
import requests
from .const import DOMAIN, DEFAULT_NAME

# https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes

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
        {"key": "wodne", "name": "Water", "device_class": SensorDeviceClass.POWER, "unit": UnitOfPower.MEGA_WATT},
        {"key": "wiatrowe", "name": "Wind", "device_class": SensorDeviceClass.POWER, "unit": UnitOfPower.MEGA_WATT},
        {"key": "PV", "name": "Sun", "device_class": SensorDeviceClass.POWER, "unit": UnitOfPower.MEGA_WATT},
        {"key": "generacja", "name": "Production", "device_class": SensorDeviceClass.POWER, "unit": UnitOfPower.MEGA_WATT},
        {"key": "zapotrzebowanie", "name": "Demand", "device_class": SensorDeviceClass.POWER, "unit": UnitOfPower.MEGA_WATT},
        {"key": "cieplne", "name": "cieplne", "device_class": SensorDeviceClass.POWER, "unit": UnitOfPower.MEGA_WATT},
        {"key": "power_demand_coverage", "name": "Power Demand Coverage", "unit": "%"},
        {"key": "power_renewable", "name": "Renewable Share", "unit": "%"},
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
        # {"status":"0","timestamp":1741901100661,"data":{
        # "przesyly":[{"wartosc":559,"rownolegly":false,"wartosc_plan":562,"id":"SE"},{"wartosc":-1415,"rownolegly":true,"wartosc_plan":-2405,"id":"DE"},{"wartosc":-1142,"rownolegly":true,"wartosc_plan":-452,"id":"CZ"},{"wartosc":-489,"rownolegly":true,"wartosc_plan":-130,"id":"SK"},{"wartosc":39,"rownolegly":false,"wartosc_plan":0,"id":"UA"},{"wartosc":-123,"rownolegly":false,"wartosc_plan":-39,"id":"LT"}],
        # "podsumowanie":{"wodne":145,"wiatrowe":3945,"PV":0,"generacja":21473,"zapotrzebowanie":18910,"czestotliwosc":50.015,"inne":0,"cieplne":17383}}}
        podsumowanie = self._coordinator.data.get("data", {}).get("podsumowanie", {})
        if self._sensor_key in podsumowanie:
            value = podsumowanie[self._sensor_key]
#            if self._sensor_key == "timestamp":
#                return dt_util.parse_datetime(value)
            return value
        if self._sensor_key == "power_demand_coverage":
            return round(podsumowanie["generacja"] / podsumowanie["zapotrzebowanie"] * 100, 2)
        if self._sensor_key == "power_renewable":
            # assume `inne` is renewable
            generacja = podsumowanie["generacja"]
            cieplne = podsumowanie["cieplne"]
            return round((generacja - cieplne) / generacja * 100, 2)
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._attr_unit_of_measurement

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

#TODO#class KompasEnergetycznyPowerSensor(SensorEntity): # technology power [MW]
#TODO#class KompasEnergetycznyPowerShareSensor(SensorEntity): # % of total production per technology [%]
#TODO#class KompasEnergetycznyRenewablePowerShare(SensorEntity): # % of renewables
