"""Constants for Kompas Energetyczny"""

DOMAIN = "kompas_energetyczny"
MANUFACTURER = "Energetyczny Kompas"
DEFAULT_NAME = "Kompas Energetyczny"
HOME_URL = "https://www.energetycznykompas.pl/"

# Value rounding precision, namely percentage
PRECISION = 2

API_URL_PRZESYLY = "https://kompasen-dcgbapbjg3fkb5gp.a01.azurefd.net/datafile/przesyly.json"
API_URL_RAPORTY_V2 = 'https://api.raporty.pse.pl/api/pdgsz?$filter=dtime%20gt%20%27{}%27%20and%20is_active%20eq%20true'

STATUS_MAP = {
    0: "zalecane_uzytkowanie",
    1: "normalne_uzytkowanie",
    2: "zalecane_oszczedzanie",
    3: "wymagane_ograniczenie",
}

STATUS_MAP_SHORT = {
    0: "ZU",
    1: "NU",
    2: "ZO",
    3: "WO",
}
