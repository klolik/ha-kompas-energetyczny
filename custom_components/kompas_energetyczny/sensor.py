"""Sensors for Kompas Energetyczny"""
# https://developers.home-assistant.io/docs/core/entity/sensor/

import logging
from datetime import datetime
import dateutil.tz
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
    #TODO# config flow to disable certain sensors
    sensors = [
        {"key": "wodne", "name": "Hydro"},
        {"key": "wiatrowe", "name": "Wind"},
        {"key": "PV", "name": "Solar"},
        {"key": "generacja", "name": "Production"},
        {"key": "zapotrzebowanie", "name": "Consumption"},
        {"key": "cieplne", "name": "Fossil"},
        {"key": "renewable", "name": "Renewable"},
    ]

    entities = [ KompasEnergetycznyPowerSensor(api_data, **cfg) for cfg in sensors ]
    # generacja_share would always be 100% of generacja, so skip it
    entities.extend([KompasEnergetycznyPowerGenerationShareSensor(api_data, **cfg) for cfg in sensors if cfg["key"] not in ["generacja", "zapotrzebowanie"]])
    entities.append(KompasEnergetycznyPowerConsumptionShareSensor(api_data, "generacja", "Consumption"))
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
        self._attr_unique_id = f"{self.api_data.coordinator.config_entry.entry_id}_{sid}"
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


class KompasEnergetycznyStatusSensor(KompasEnergetycznyBaseSensor):
    """Energy Use Recommendation Sensor"""
    def __init__(self, api_data: KompasEnergetycznyApiData) -> None:
        super().__init__(api_data, None, "status", "Status")
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(STATUS_MAP.values())
        self._attr_state_class = None

    def get_znacznik(self):
        """ Return raw value of `usage_fcst` (former `znacznik` in API v1) property"""
        pdgsz = self.api_data.coordinator_pdgsz.data.get("value", [])
        now = dt_util.now().replace(minute=0, second=0, microsecond=0)
        _LOGGER.debug("now: %s", now)
        #_LOGGER.debug("pdgsz: %s", pdgsz)
        for item in pdgsz:
            if datetime.fromisoformat(item.get("dtime")).astimezone(dateutil.tz.tzlocal()) == now:
                _LOGGER.debug("found item: %s", item)
                return item.get("usage_fcst")
        _LOGGER.error("Usage forcecast status not found for %s in %s", now, pdgsz)
        return None

    @property
    def native_value(self):
        znacznik = self.get_znacznik()
        return STATUS_MAP.get(znacznik, None)

    @property
    def extra_state_attributes(self):
        znacznik = self.get_znacznik()
        return {**self.api_data.coordinator_pdgsz.data, "znacznik": znacznik}
