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
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, DEFAULT_NAME, STATUS_MAP
from .entity import KompasEnergetycznyApiData


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    """Setup entry"""
    api_data = hass.data[DOMAIN][entry.entry_id]

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

    entities = [ KompasEnergetycznyPowerSensor(api_data, **cfg) for cfg in sensors ]
    # generacja_share would always be 100% of generacja, so skip it
    entities.extend([ KompasEnergetycznyPowerGenerationShareSensor(api_data, **cfg) for cfg in sensors if cfg["key"] not in ["generacja", "zapotrzebowanie"]])
    entities.append(KompasEnergetycznyPowerConsumptionShareSensor(api_data, "generacja", "Consumption"))
    entities.append(KompasEnergetycznyRenewableShareSensor(api_data))
    entities.append(KompasEnergetycznyPowerImportSensor(api_data))

    entities.append(KompasEnergetycznyStatusSensor(api_data))

    async_add_entities(entities)
    return True


class KompasEnergetycznyBaseSensor(SensorEntity):
    """Base class with common attributes"""

    def __init__(self, api_data: KompasEnergetycznyApiData, src: str, sid: str, name: str) -> None:
        """Initialize sensor with src: json data key, sid: entity id, name: display name"""
        super().__init__()
        _LOGGER.debug("setting up %s", sid)
        self.api_data = api_data
        self._podsumowanie_key = src
        self._attr_name = f"{DEFAULT_NAME} {name}"
        self._attr_unique_id = f"{self.api_data.coordinator.entry.entry_id}_{sid}"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = self.api_data.device

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.api_data.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self.api_data.coordinator.last_update_success


class KompasEnergetycznyPowerSensor(KompasEnergetycznyBaseSensor):
    """Generic Power Sensor"""
    def __init__(self, api_data: KompasEnergetycznyApiData, key: str, name: str) -> None:
        super().__init__(api_data, key, key, f"{name} Power")
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        podsumowanie = self.api_data.coordinator.data.get("data", {}).get("podsumowanie", {})
        # we shall return None if missing, so just pass through None as well
        return podsumowanie.get(self._podsumowanie_key)


class KompasEnergetycznyPowerImportSensor(KompasEnergetycznyBaseSensor):
    """Power Import Sensor"""
    def __init__(self, api_data: KompasEnergetycznyApiData) -> None:
        super().__init__(api_data, None, "power_import", "Power Import")
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        podsumowanie = self.api_data.coordinator.data.get("data", {}).get("podsumowanie", {})
        generacja = podsumowanie.get("generacja")
        zapotrzebowanie = podsumowanie.get("zapotrzebowanie")
        if generacja is not None and zapotrzebowanie is not None:
            return zapotrzebowanie - generacja
        return None


class KompasEnergetycznyPowerGenerationShareSensor(KompasEnergetycznyBaseSensor):
    """Power Generation Share Sensor"""
    def __init__(self, api_data: KompasEnergetycznyApiData, key: str, name: str) -> None:
        super().__init__(api_data, key, f"{key}_share", f"{name} Share")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self):
        podsumowanie = self.api_data.coordinator.data.get("data", {}).get("podsumowanie", {})
        value = podsumowanie.get(self._podsumowanie_key)
        generacja = podsumowanie.get("generacja")
        if value is not None and generacja is not None:
            return value / generacja * 100
        return None


class KompasEnergetycznyPowerConsumptionShareSensor(KompasEnergetycznyBaseSensor):
    """Power Consumption Share Sensor"""
    def __init__(self, api_data: KompasEnergetycznyApiData, key: str, name: str) -> None:
        super().__init__(api_data, key, f"{key}_coverage", f"{name} Coverage")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self):
        podsumowanie = self.api_data.coordinator.data.get("data", {}).get("podsumowanie", {})
        value = podsumowanie.get(self._podsumowanie_key)
        zapotrzebowanie = podsumowanie.get("zapotrzebowanie")
        if value is not None and zapotrzebowanie is not None:
            return value / zapotrzebowanie * 100
        return None


class KompasEnergetycznyRenewableShareSensor(KompasEnergetycznyBaseSensor):
    """Renewable Power Share Sensor"""
    def __init__(self, api_data: KompasEnergetycznyApiData) -> None:
        super().__init__(api_data, None, "renewable_share", "Renewable Share")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self):
        podsumowanie = self.api_data.coordinator.data.get("data", {}).get("podsumowanie", {})
        generacja = podsumowanie.get("generacja")
        cieplne = podsumowanie.get("cieplne")
        if generacja is not None and cieplne is not None:
            return (generacja - cieplne) / generacja * 100
        return None



class KompasEnergetycznyStatusSensor(KompasEnergetycznyBaseSensor):
    """Energy Use Recommendation Sensor"""
    def __init__(self, api_data: KompasEnergetycznyApiData) -> None:
        super().__init__(api_data, None, "status", "Status")
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(STATUS_MAP.values())
        self._attr_state_class = None

    @property
    def native_value(self):
        pdgsz = self.api_data.coordinator_pdgsz.data.get("value", [])
        now_hour = dt_util.now().hour
        _LOGGER.debug("now_hour: %s", now_hour)
        _LOGGER.debug("pdgsz: %s", pdgsz)
        for item in pdgsz:
            if datetime.fromisoformat(item.get("udtczas")).hour == now_hour:
                return STATUS_MAP.get(item.get("znacznik"))
        return None

    @property
    def extra_state_attributes(self):
        return self.api_data.coordinator_pdgsz.data
