"""Constants for Kompas Energetyczny"""

DOMAIN = "kompas_energetyczny"
MANUFACTURER = "Energetyczny Kompas"
DEFAULT_NAME = "Kompas Energetyczny"
HOME_URL = "https://www.energetycznykompas.pl/"

# Value rounding precision, namely percentage
PRECISION = 2

API_URL_PRZESYLY = "https://kompasen-dcgbapbjg3fkb5gp.a01.azurefd.net/datafile/przesyly.json"
API_URL_SZCZYT = 'https://v1.api.raporty.pse.pl/api/pdgsz?$filter=business_date%20eq%20%27{}%27'

STATUS_MAP = {
    0: "Zalecane uzytkowanie",
    1: "Normalne uzytkowanie",
    2: "Zalecane oszczedzanie",
    3: "Wymagane ograniczenie",
}
