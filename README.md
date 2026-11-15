# strommix-at

Analyse des österreichischen Stromsystems mit Python und SQL: Woher kommt der Strom,
wie verläuft der Verbrauch über den Tag, und was verdienen Solaranlagen und Pumpspeicher
am Markt?

**Stand:** Die Daten werden geladen und liegen in einer Datenbank. Validierung und
Auswertungen folgen (siehe [Nächste Schritte](#nächste-schritte)).

## Daten

Quelle ist die öffentliche Schnittstelle von [Energy-Charts](https://www.energy-charts.info)
(Fraunhofer ISE). Verwendet werden zwei Endpunkte für Österreich, Zeitraum Jänner 2024:

| Endpunkt | Inhalt | Einheit | Auflösung am 1.1.2024 |
| --- | --- | --- | --- |
| `public_power` | Erzeugung je Kraftwerksart, Last, Speicher, Stromhandel | MW (mittlere Leistung im Intervall) | 15 Minuten |
| `price` | Day-Ahead-Preis der Gebotszone AT | EUR/MWh | 60 Minuten |

Die Preisdaten stammen laut Schnittstelle von Bundesnetzagentur | SMARD.de und stehen
unter der Lizenz CC BY 4.0.

### Was bei diesen Daten zu beachten ist

- **Zeit:** Die Zeitstempel sind Unix-Sekunden in UTC und markieren den Beginn des
  Intervalls. Der erste Wert des 1. Jänner 2024 ist 23:00 UTC am Vortag, also
  Mitternacht in Wien.
- **Leistung und Energie:** Die Werte sind Leistungen. Energie in MWh ergibt sich aus
  Leistung mal Intervalllänge, bei Viertelstunden also MW mal 0,25 h.
- **Vorzeichen:** Der Pumpbetrieb der Speicher (`Hydro pumped storage consumption`) ist
  null oder negativ, weil er dem Netz Leistung entnimmt. Beim Stromhandel ist Import
  positiv und Export negativ.
- **Verschiedene Auflösung:** Zu einem Stundenpreis gehören vier Leistungswerte. Vor dem
  Verbinden wird die Leistung über die Stunde gemittelt.

### Kategorien der Reihen

| Kategorie | Reihen |
| --- | --- |
| Erzeugung | Hydro Run-of-River, Hydro water reservoir, Wind onshore, Solar, Biomass, Geothermal, Waste, Fossil gas, Others |
| Speicher | Hydro pumped storage, Hydro pumped storage consumption |
| Handel | Cross border electricity trading |
| Last | Load |
| Abgeleitet | Residual load, Renewable share of load, Renewable share of generation |

Die abgeleiteten Reihen berechnet der Anbieter selbst, zwei davon sind Prozentwerte. Sie
gehen in keine Summe ein und dienen nur dazu, die eigenen Berechnungen zu überprüfen.

## Aufbau der Datenbank

`load.py` schreibt drei Tabellen in die Datei `data/strommix.duckdb`:

| Tabelle | Eine Zeile ist | Spalten |
| --- | --- | --- |
| `power` | ein Zeitpunkt und eine Reihe | `time_key`, `ts_utc`, `ts_local`, `series`, `value_mw` |
| `price` | ein Zeitpunkt | `time_key`, `ts_utc`, `ts_local`, `price_eur_mwh` |
| `series_category` | eine Reihe | `series`, `category` |

`time_key` sind die Unix-Sekunden der Quelle. `ts_local` ist die Wiener Uhrzeit und dient
zum Gruppieren nach Tagesstunde.

Die Antworten der Schnittstelle werden unverändert unter `data/raw/` abgelegt und bei
einem weiteren Lauf wiederverwendet. Die Tabellen werden bei jedem Lauf neu aufgebaut,
sodass wiederholtes Laden keine doppelten Zeilen erzeugt.

## Starten

Voraussetzung ist Python 3.11 oder neuer. Befehle für Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python load.py
```

Ein anderer Zeitraum lässt sich als erster und letzter Tag angeben:

```powershell
python load.py 2024-01-01 2024-01-01
```

Für den 1. Jänner 2024 meldet das Skript 1536 Zeilen in `power` (96 Zeitpunkte mal
16 Reihen) und 24 Zeilen in `price`.

## Nächste Schritte

- [ ] Validierung: eigene Residuallast (Last minus Wind minus Solar) gegen die Reihe des
      Anbieters, Prüfung auf Lücken und falsche Vorzeichen
- [ ] Auswertung 1: Energie und Anteil je Erzeugungsart
- [ ] Auswertung 2: mittleres Tagesprofil von Last und Solar
- [ ] Auswertung 3: steilste Änderungen der Residuallast
- [ ] Auswertung 4: Marktwert von Solarstrom im Vergleich zum Durchschnittspreis
- [ ] Auswertung 5: Preise beim Pumpen und beim Erzeugen der Pumpspeicher
- [ ] Zwei Grafiken und die wichtigsten Ergebnisse in dieser README

## Grenzen

- Nur Österreich und nur ein Monat.
- Die Zuordnung der Reihen zu Kategorien ist von Hand festgelegt. Liefert die
  Schnittstelle eine unbekannte Reihe, bricht `load.py` mit einer Fehlermeldung ab.
- `ts_local` ist in der Nacht der Zeitumstellung im Oktober nicht eindeutig. Für den
  Jänner spielt das keine Rolle.
- Keine automatisierten Tests.
