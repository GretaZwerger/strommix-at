"""Führt eine SQL-Datei auf der Datenbank aus und zeigt das Ergebnis.

Aufruf:
    python run_sql.py sql/auswertung/01_energie_pro_quelle.sql
"""

import sys
from pathlib import Path

import duckdb

if len(sys.argv) != 2:
    sys.exit("Aufruf: python run_sql.py PFAD_ZUR_SQL_DATEI")

query = Path(sys.argv[1]).read_text(encoding="utf-8")
with duckdb.connect("data/strommix.duckdb", read_only=True) as con:
    con.sql(query).show(max_rows=50, max_width=200)
