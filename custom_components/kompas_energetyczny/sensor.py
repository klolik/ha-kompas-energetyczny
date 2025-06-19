"""Sensors for Kompas Energetyczny"""
# https://developers.home-assistant.io/docs/core/entity/sensor/

# $ curl https://kompasen-dcgbapbjg3fkb5gp.a01.azurefd.net/datafile/przesyly.json
# {"status":"0","timestamp":1741901100661,"data":{
#   "przesyly":[
#       {"wartosc":559,"rownolegly":false,"wartosc_plan":562,"id":"SE"},
#       {"wartosc":-1415,"rownolegly":true,"wartosc_plan":-2405,"id":"DE"},
#       {"wartosc":-1142,"rownolegly":true,"wartosc_plan":-452,"id":"CZ"},
#       {"wartosc":-489,"rownolegly":true,"wartosc_plan":-130,"id":"SK"},
#       {"wartosc":39,"rownolegly":false,"wartosc_plan":0,"id":"UA"},
#       {"wartosc":-123,"rownolegly":false,"wartosc_plan":-39,"id":"LT"}
#   ],
#   "podsumowanie":{"wodne":145,"wiatrowe":3945,"PV":0,"generacja":21473,"zapotrzebowanie":18910,"czestotliwosc":50.015,"inne":0,"cieplne":17383}
# }}

# $ curl -s 'https://v1.api.raporty.pse.pl/api/pdgsz?$filter=business_date%20eq%20%272025-06-19%27' |jq .
#
# {
#   "value": [
#     {
#       "udtczas": "2025-06-19 00:00:00",
#       "zap_kse": 0,
#       "znacznik": 1, # 0: zalecane uzytkowanie, 1: normalne uzytkowanie, 2: zalecane oszczedzanie, 3: wymagane ograniczenie
#       "business_date": "2025-06-19",
#       "source_datetime": "2025-06-19 17:22"
#     },
#     [...]
#   ]
# }
#

import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
import requests
from .const import DOMAIN, MANUFACTURER, DEFAULT_NAME, HOME_URL, PRECISION, URL_PDGSZ, STATUS_MAP


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    _LOGGER.debug("setting up coordinator for %s", entry)
    coordinator = KompasEnergetycznyDataUpdateCoordinator(hass, entry)
    _LOGGER.debug("awaiting coordinator first refresh %s", entry)
    await coordinator.async_config_entry_first_refresh()

    _LOGGER.debug("setting up pdgsz coordinator for %s", entry)
    coordinator_pdgsz = KompasEnergetycznyPdgszDataUpdateCoordinator(hass, entry)
    _LOGGER.debug("awaiting pdgsz coordinator first refresh %s", entry)
    await coordinator_pdgsz.async_config_entry_first_refresh()

    _LOGGER.debug("assigning coordinator %s", entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "coordinator_pdgsz": coordinator_pdgsz,
    }

    _LOGGER.debug("setting up sensors")
    #TODO# support user controls to disable certain sensors
    sensors = [
        {"key": "wodne", "name": "Hydro"},
        {"key": "wiatrowe", "name": "Wind"},
        {"key": "PV", "name": "Solar"},
        {"key": "generacja", "name": "Production"},
        {"key": "zapotrzebowanie", "name": "Consumption"},
        {"key": "cieplne", "name": "Fossil"},
    ]

    entities = [ KompasEnergetycznyPowerSensor(coordinator, **cfg) for cfg in sensors ]
    # generacja_share would always be 100% of generacja, so skip it
    entities.extend([ KompasEnergetycznyPowerGenerationShareSensor(coordinator, **cfg) for cfg in sensors if cfg["key"] not in ["generacja", "zapotrzebowanie"]])
    entities.append(KompasEnergetycznyPowerConsumptionShareSensor(coordinator, "generacja", "Consumption"))
    entities.append(KompasEnergetycznyRenewableShareSensor(coordinator))
    entities.append(KompasEnergetycznyPowerImportSensor(coordinator))
    entities.append(KompasEnergetycznyStatusSensor(coordinator_pdgsz))

    async_add_entities(entities)
    return True


class KompasEnergetycznyDataUpdateCoordinator(DataUpdateCoordinator):
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

class KompasEnergetycznySensor(SensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, sensor_config: dict) -> None:
        super().__init__()
        _LOGGER.debug("setting up %s", sensor_config)
        self._coordinator = coordinator
        self._sensor_key = sensor_config["key"]
        self._attr_name = f"{DEFAULT_NAME} {sensor_config['name']}"
        self._attr_unique_id = f"{self._coordinator.entry.entry_id}_{self._sensor_key}"
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_suggested_display_precision = PRECISION
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, DOMAIN)},
            manufacturer=MANUFACTURER,
            name=DEFAULT_NAME,
            configuration_url=HOME_URL,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

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
            return podsumowanie["generacja"] / podsumowanie["zapotrzebowanie"] * 100
        if self._sensor_key == "power_renewable":
            # assume `inne` is renewable
            generacja = podsumowanie["generacja"]
            cieplne = podsumowanie["cieplne"]
            return (generacja - cieplne) / generacja * 100
        return None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )


class KompasEnergetycznyBaseSensor(SensorEntity):
    """Base class with common attributes"""

    def __init__(self, coordinator: DataUpdateCoordinator, src: str, sid: str, name: str) -> None:
        """Initialize sensor with src: json data key, sid: entity id, name: display name"""
        super().__init__()
        _LOGGER.debug("setting up %s", sid)
        self._coordinator = coordinator
        self._podsumowanie_key = src
        self._attr_name = f"{DEFAULT_NAME} {name}"
        self._attr_unique_id = f"{self._coordinator.entry.entry_id}_{sid}"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, DOMAIN)},
            manufacturer=MANUFACTURER,
            name=DEFAULT_NAME,
            configuration_url=HOME_URL,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success


class KompasEnergetycznyPowerSensor(KompasEnergetycznyBaseSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key, key, f"{name} Power")
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        podsumowanie = self._coordinator.data.get("data", {}).get("podsumowanie", {})
        # we shall return None if missing, so just pass through None as well
        return podsumowanie.get(self._podsumowanie_key)


class KompasEnergetycznyPowerImportSensor(KompasEnergetycznyBaseSensor):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator, None, "power_import", "Power Import")
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        podsumowanie = self._coordinator.data.get("data", {}).get("podsumowanie", {})
        generacja = podsumowanie.get("generacja")
        zapotrzebowanie = podsumowanie.get("zapotrzebowanie")
        if generacja is not None and zapotrzebowanie is not None:
            return zapotrzebowanie - generacja
        return None


class KompasEnergetycznyPowerGenerationShareSensor(KompasEnergetycznyBaseSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key, f"{key}_share", f"{name} Share")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self):
        podsumowanie = self._coordinator.data.get("data", {}).get("podsumowanie", {})
        value = podsumowanie.get(self._podsumowanie_key)
        generacja = podsumowanie.get("generacja")
        if value is not None and generacja is not None:
            return value / generacja * 100
        return None


class KompasEnergetycznyPowerConsumptionShareSensor(KompasEnergetycznyBaseSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key, f"{key}_coverage", f"{name} Coverage")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self):
        podsumowanie = self._coordinator.data.get("data", {}).get("podsumowanie", {})
        value = podsumowanie.get(self._podsumowanie_key)
        zapotrzebowanie = podsumowanie.get("zapotrzebowanie")
        if value is not None and zapotrzebowanie is not None:
            return value / zapotrzebowanie * 100
        return None


class KompasEnergetycznyRenewableShareSensor(KompasEnergetycznyBaseSensor):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator, None, "renewable_share", "Renewable Share")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self):
        podsumowanie = self._coordinator.data.get("data", {}).get("podsumowanie", {})
        generacja = podsumowanie.get("generacja")
        cieplne = podsumowanie.get("cieplne")
        if generacja is not None and cieplne is not None:
            return (generacja - cieplne) / generacja * 100
        return None


class KompasEnergetycznyPdgszDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.debug("initializing pdgsz coordinator: %s", entry)
        super().__init__(hass, _LOGGER, name=entry.title, update_interval=timedelta(seconds=300))
        self.entry = entry
        self.data = None

    async def _async_update_data(self):
        try:
            today = dt_util.now() #TODO# ensure its Poland time zone aware
            url = URL_PDGSZ.format(today.strftime("%Y-%m-%d"))
            _LOGGER.debug("calling pdgsz %s", url)
            response = await self.hass.async_add_executor_job(requests.get, url)
            response.raise_for_status()
            self.raw_data = response.json()
            self.data = self.raw_data
            _LOGGER.debug("received pdgsz %s", self.data)
            return self.data
        except requests.exceptions.RequestException as ex:
            raise UpdateFailed(f"Error communicating with pdgsz API: {ex}") from ex


class KompasEnergetycznyStatusSensor(KompasEnergetycznyBaseSensor):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator, None, "status", "Status")
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(STATUS_MAP.values())
        self._attr_state_class = None

    @property
    def native_value(self):
        pdgsz = self._coordinator.data.get("value", [])
        now_hour = dt_util.now().hour
        _LOGGER.debug("now_hour: %s", now_hour)
        _LOGGER.debug("pdgsz: %s", pdgsz)
        for item in pdgsz:
#            _LOGGER.debug("item: %s", item)
            if datetime.fromisoformat(item.get("udtczas")).hour == now_hour:
                return STATUS_MAP.get(item.get("znacznik"))
        return None

    @property
    def extra_state_attributes(self):
        return self._coordinator.data
