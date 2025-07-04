"""Constants for Kompas Energetyczny"""

DOMAIN = "kompas_energetyczny"
MANUFACTURER = "Energetyczny Kompas"
DEFAULT_NAME = "Kompas Energetyczny"
HOME_URL = "https://www.energetycznykompas.pl/"

# Value rounding precision, namely percentage
PRECISION = 2

API_URL_PRZESYLY = (
    "https://kompasen-dcgbapbjg3fkb5gp.a01.azurefd.net/datafile/przesyly.json"
)
API_URL_RAPORTY_V2 = "https://v2.api.raporty.pse.pl/api/pdgsz?%24filter=dtime%20gt%20%27{}%27%20and%20is_active%20eq%20true"

STATUS_MAP = {
    0: "Zalecane uzytkowanie",
    1: "Normalne uzytkowanie",
    2: "Zalecane oszczedzanie",
    3: "Wymagane ograniczenie",
}
