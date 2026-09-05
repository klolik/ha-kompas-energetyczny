"""Constants for Kompas Energetyczny"""

DOMAIN = "kompas_energetyczny"
MANUFACTURER = "Energetyczny Kompas"
DEFAULT_NAME = "Kompas Energetyczny"
HOME_URL = "https://www.energetycznykompas.pl/"

# Value rounding precision, namely percentage
PRECISION = 2

API_URL_PRZESYLY = "https://files.energetycznykompas.pl/datafile/przesyly.json"
API_URL_RAPORTY_V2 = 'https://api.raporty.pse.pl/api/pdgsz?$filter=dtime%20gt%20%27{}%27%20and%20is_active%20eq%20true'

STATUS_MAP = {
    0: "recommended_use",    # Zalecane uzytkowanie
    1: "normal_use",         # Normalne uzytkowanie
    2: "recommended_saving", # Zalecane oszczedzanie
    3: "required_reduction", # Wymagane ograniczenie
}

STATUS_MAP_SHORT = {
    0: "ru", # ZU
    1: "nu", # NU
    2: "rs", # ZO
    3: "rr", # WO
}
