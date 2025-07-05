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

from .const import API_URL_RAPORTY_V2

_LOGGER = logging.getLogger(__name__)


# $ curl https://kompasen-dcgbapbjg3fkb5gp.a01.azurefd.net/datafile/przesyly.json
# {
#   "status":"0",
#   "timestamp":1741901100661,
#   "data":{
#     "przesyly":[
#       {"wartosc":559,"rownolegly":false,"wartosc_plan":562,"id":"SE"},
#       {"wartosc":-1415,"rownolegly":true,"wartosc_plan":-2405,"id":"DE"},
#       {"wartosc":-1142,"rownolegly":true,"wartosc_plan":-452,"id":"CZ"},
#       {"wartosc":-489,"rownolegly":true,"wartosc_plan":-130,"id":"SK"},
#       {"wartosc":39,"rownolegly":false,"wartosc_plan":0,"id":"UA"},
#       {"wartosc":-123,"rownolegly":false,"wartosc_plan":-39,"id":"LT"}
#     ],
#     "podsumowanie":{
#       "wodne":145,
#       "wiatrowe":3945,
#       "PV":0,
#       "generacja":21473,
#       "zapotrzebowanie":18910,
#       "czestotliwosc":50.015,
#       "inne":0,
#       "cieplne":17383
#     }
#   }
# }

class KompasEnergetycznyDataUpdateCoordinator(DataUpdateCoordinator):
    """Power data polling coordinator"""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.debug("initializing coordinator: %s", entry)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=300)
        )
        self.url = entry.data.get("url")
        _LOGGER.debug("url: %s", self.url)
        self.data = None

    async def _async_update_data(self):
        try:
            _LOGGER.debug("calling %s", self.url)
            response = await self.hass.async_add_executor_job(requests.get, self.url)
            response.raise_for_status()
            self.data = response.json()
            _LOGGER.debug("received %s", response.text)

            # `renewable` instead of `odnawialne` to maintain the same unique_id
            podsumowanie = self.data["data"]["podsumowanie"]
            if "renewable" not in podsumowanie:
                podsumowanie["renewable"] = podsumowanie["generacja"] - podsumowanie["cieplne"]

            return self.data
        except requests.exceptions.RequestException as ex:
            raise UpdateFailed(f"Error communicating with API: {ex}") from ex


# $ curl -s 'https://v1.api.raporty.pse.pl/api/pdgsz?$filter=business_date%20eq%20%272025-06-19%27' |jq .
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
# $ curl -s 'https://v2.api.raporty.pse.pl/api/pdgsz?%24filter=dtime%20gt%20%272025-06-25%27%20and%20is_active%20eq%20true' |jq .
# {
#   "value": [
#     {
#       "dtime": "2025-06-25 00:00",
#       "dtime_utc": "2025-06-24 22:00",
#       "is_active": true,
#       "usage_fcst": 1, # 0: zalecane uzytkowanie, 1: normalne uzytkowanie, 2: zalecane oszczedzanie, 3: wymagane ograniczenie
#       "valid_to_ts": null,
#       "business_date": "2025-06-25",
#       "valid_from_ts": "2025-06-25 12:20:36.622",
#       "publication_ts": "2025-06-25 12:20:36.622",
#       "publication_ts_utc": "2025-06-25 10:20:36.622",
#       "total_power_demand": null
#     },
#     [...]
#   ]
# }

class KompasEnergetycznyPdgszDataUpdateCoordinator(DataUpdateCoordinator):
    """Peak Hours data polling coordinator"""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.debug("initializing pdgsz coordinator: %s", entry)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=300)
        )
        self.data = None

    async def _async_update_data(self):
        try:
            today = dt_util.now() #TODO# ensure its Poland time zone aware
            url = API_URL_RAPORTY_V2.format(today.strftime("%Y-%m-%d"))
            _LOGGER.debug("calling pdgsz %s", url)
            response = await self.hass.async_add_executor_job(requests.get, url)
            response.raise_for_status()
            self.data = response.json()
            _LOGGER.debug("received pdgsz %s", response.text)
            return self.data
        except requests.exceptions.RequestException as ex:
            raise UpdateFailed(f"Error communicating with pdgsz API: {ex}") from ex


@dataclass
class KompasEnergetycznyApiData:
    """hass.data DOMAIN entry data"""
    device: DeviceInfo
    coordinator: KompasEnergetycznyDataUpdateCoordinator
    coordinator_pdgsz: KompasEnergetycznyPdgszDataUpdateCoordinator
