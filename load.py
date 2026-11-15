"""Lädt österreichische Stromdaten von Energy-Charts in eine DuckDB-Datenbank.

Aufruf:
    python load.py                          # Jänner 2024 (Standard)
    python load.py 2024-01-01 2024-01-01    # anderer Zeitraum: erster und letzter Tag

Ergebnis: data/strommix.duckdb mit drei Tabellen
    power            eine Zeile pro Zeitpunkt und Reihe, mittlere Leistung in MW
    price            eine Zeile pro Zeitpunkt, Day-Ahead-Preis in EUR/MWh
    series_category  ordnet jede Reihe einer Kategorie zu
"""

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests

API = "https://api.energy-charts.info"
COUNTRY = "at"  # Parameter des Endpunkts public_power
BIDDING_ZONE = "AT"  # Parameter des Endpunkts price
LOCAL_TZ = "Europe/Vienna"

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "strommix.duckdb"

# Kategorie jeder Reihe. Die abgeleiteten Reihen berechnet der Anbieter selbst;
# sie dürfen nie in eine Summe über Megawatt einfließen (zwei davon sind Prozentwerte).
CATEGORIES = {
    "Hydro Run-of-River": "erzeugung",
    "Hydro water reservoir": "erzeugung",
    "Wind onshore": "erzeugung",
    "Solar": "erzeugung",
    "Biomass": "erzeugung",
    "Geothermal": "erzeugung",
    "Waste": "erzeugung",
    "Fossil gas": "erzeugung",
    "Others": "erzeugung",
    "Hydro pumped storage": "speicher",  # Turbinenbetrieb, Werte >= 0
    "Hydro pumped storage consumption": "speicher",  # Pumpbetrieb, Werte <= 0
    "Cross border electricity trading": "handel",  # Import > 0, Export < 0
    "Load": "last",
    "Residual load": "abgeleitet",  # MW
    "Renewable share of load": "abgeleitet",  # Prozent
    "Renewable share of generation": "abgeleitet",  # Prozent
}


def fetch(endpoint: str, params: dict, start: str, end: str) -> dict:
    """Holt eine Antwort der Schnittstelle und legt sie unverändert unter data/raw/ ab.

    Liegt die Datei schon vor, wird sie gelesen statt neu abgerufen. So bleibt ein
    zweiter Lauf ohne Netzwerkzugriff, und die Rohdaten sind die nachprüfbare Grundlage.
    """
    path = RAW_DIR / f"{endpoint}_{start}_{end}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    response = requests.get(
        f"{API}/{endpoint}", params={**params, "start": start, "end": end}, timeout=60
    )
    response.raise_for_status()  # bricht bei HTTP-Fehlern ab, statt eine Fehlerseite zu speichern
    payload = response.json()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def add_timestamps(frame: pd.DataFrame) -> pd.DataFrame:
    """Ergänzt lesbare Zeitspalten zu den Unix-Sekunden in time_key.

    ts_utc ist eindeutig. ts_local ist die Wiener Uhrzeit ohne Zeitzonenangabe; sie dient
    nur zum Gruppieren nach Ortsstunde. In der Nacht der Zeitumstellung im Oktober kommt
    dieselbe Ortsstunde zweimal vor, deshalb bleibt time_key der Schlüssel für Joins.
    """
    utc = pd.to_datetime(frame["time_key"], unit="s", utc=True)
    frame["ts_utc"] = utc.dt.tz_localize(None)
    frame["ts_local"] = utc.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    return frame


def power_to_frame(payload: dict) -> pd.DataFrame:
    """Formt die verschachtelte Leistungsantwort in eine lange Tabelle um.

    Jeder Wert ist die mittlere Leistung in MW in dem Intervall, das bei time_key beginnt.
    """
    time_keys = np.asarray(payload["unix_seconds"], dtype=np.int64)
    series = payload["production_types"]
    n_times, n_series = time_keys.size, len(series)

    # Matrix mit einer Zeile pro Reihe. JSON null wird zu NaN und später zu SQL NULL.
    values = np.empty((n_series, n_times), dtype=np.float64)
    for row, item in enumerate(series):  # Schleife über 16 Reihen, nicht über Messwerte
        data = np.asarray(item["data"], dtype=np.float64)
        if data.size != n_times:
            raise ValueError(f"Reihe {item['name']!r}: {data.size} Werte, {n_times} Zeitpunkte")
        values[row] = data

    names = np.array([item["name"] for item in series], dtype=object)
    frame = pd.DataFrame(
        {
            # values.ravel() läuft zeilenweise: erst alle Zeitpunkte der Reihe 0, dann der
            # Reihe 1 usw. Dazu passen die Zeitpunkte n_series-mal hintereinander (tile)
            # und jeder Name n_times-mal wiederholt (repeat).
            "time_key": np.tile(time_keys, n_series),
            "series": np.repeat(names, n_times),
            "value_mw": values.ravel(),
        }
    )
    return add_timestamps(frame)


def price_to_frame(payload: dict) -> pd.DataFrame:
    """Formt die Preisantwort in eine Tabelle um (Day-Ahead-Preis in EUR/MWh)."""
    unit = payload["unit"].replace(" ", "")
    if unit != "EUR/MWh":
        raise ValueError(f"Unerwartete Preiseinheit: {payload['unit']!r}")
    frame = pd.DataFrame(
        {
            "time_key": np.asarray(payload["unix_seconds"], dtype=np.int64),
            "price_eur_mwh": np.asarray(payload["price"], dtype=np.float64),
        }
    )
    return add_timestamps(frame)


def main(start: str, end: str) -> None:
    power_df = power_to_frame(fetch("public_power", {"country": COUNTRY}, start, end))
    price_df = price_to_frame(fetch("price", {"bzn": BIDDING_ZONE}, start, end))
    categories = pd.DataFrame(list(CATEGORIES.items()), columns=["series", "category"])

    # Eine Reihe ohne Kategorie würde in den Auswertungen stillschweigend fehlen.
    unknown = sorted(set(power_df["series"]) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"Reihen ohne Kategorie, bitte in CATEGORIES ergänzen: {unknown}")

    DATA_DIR.mkdir(exist_ok=True)
    with duckdb.connect(str(DB_PATH)) as con:
        # CREATE OR REPLACE baut die Tabellen bei jedem Lauf neu auf:
        # zweimal laden ergibt dieselben Zeilen, keine doppelten.
        # DuckDB liest die pandas-Tabellen power_df, price_df und categories direkt
        # über ihren Variablennamen. Sie heißen bewusst anders als die Datenbanktabellen.
        con.execute(
            """
            CREATE OR REPLACE TABLE power AS
            SELECT time_key, ts_utc, ts_local, series, value_mw FROM power_df
            """
        )
        con.execute(
            """
            CREATE OR REPLACE TABLE price AS
            SELECT time_key, ts_utc, ts_local, price_eur_mwh FROM price_df
            """
        )
        con.execute("CREATE OR REPLACE TABLE series_category AS SELECT * FROM categories")

        n_power, n_times, n_series = con.execute(
            "SELECT count(*), count(DISTINCT time_key), count(DISTINCT series) FROM power"
        ).fetchone()
        n_price = con.execute("SELECT count(*) FROM price").fetchone()[0]
        first_utc, first_local = con.execute(
            "SELECT ts_utc, ts_local FROM power ORDER BY time_key LIMIT 1"
        ).fetchone()

    print(f"power: {n_power} Zeilen ({n_times} Zeitpunkte x {n_series} Reihen)")
    print(f"price: {n_price} Zeilen")
    print(f"erster Zeitpunkt: {first_utc} UTC = {first_local} Ortszeit")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 1:
        main("2024-01-01", "2024-01-31")
    else:
        sys.exit("Aufruf: python load.py [ERSTER_TAG LETZTER_TAG], Datum als JJJJ-MM-TT")
