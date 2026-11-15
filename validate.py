"""Führt alle Prüfabfragen in sql/checks/ aus.

Jede Datei enthält genau eine Abfrage, die die FEHLERHAFTEN Zeilen zurückgibt.
Ein leeres Ergebnis bedeutet: Prüfung bestanden.
"""

import sys
from pathlib import Path

import duckdb

DB_PATH = "data/strommix.duckdb"
CHECK_DIR = Path("sql/checks")

failed = 0
with duckdb.connect(DB_PATH, read_only=True) as con:
    for path in sorted(CHECK_DIR.glob("*.sql")):
        result = con.sql(path.read_text(encoding="utf-8"))
        n_rows = len(result.fetchall())
        if n_rows == 0:
            print(f"ok      {path.stem}")
        else:
            failed += 1
            print(f"FEHLER  {path.stem}: {n_rows} Zeilen")
            con.sql(path.read_text(encoding="utf-8")).show(max_rows=10)

sys.exit(1 if failed else 0)