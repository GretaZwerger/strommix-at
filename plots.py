"""Erstellt zwei Grafiken des Projekts aus der Datenbank.

Aufruf:
    python plots.py

Ergebnis:
    figures/tagesprofil.png         mittleres Tagesprofil von Last und Solar
    figures/preis_residuallast.png  Day-Ahead-Preis gegen Residuallast, ein Punkt pro Stunde
"""

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt

DB_PATH = "data/strommix.duckdb"
FIG_DIR = Path("figures")

# Farben: Kategoriepalette (Blau, Orange) und Grau-Töne für Text und Raster.
BLAU = "#2a78d6"
ORANGE = "#eb6834"
TEXT = "#0b0b0b"
TEXT_LEISE = "#52514e"
RASTER = "#e4e3df"

# Mittleres Tagesprofil: für jede Ortsstunde der Mittelwert über alle Tage.
# Alle Intervalle sind 15 Minuten lang, daher ist der einfache Mittelwert zeitgewichtet.
SQL_TAGESPROFIL = """
SELECT
    hour(ts_local)                                AS stunde,
    avg(value_mw) FILTER (WHERE series = 'Load')  AS last_mw,
    avg(value_mw) FILTER (WHERE series = 'Solar') AS solar_mw
FROM power
WHERE series IN ('Load', 'Solar')
GROUP BY hour(ts_local)
ORDER BY stunde
"""

# Residuallast auf Stunden mitteln und mit dem Stundenpreis verbinden,
# nach derselben Methode wie in Abfrage 4.
SQL_PREIS_RESIDUALLAST = """
WITH residual_stunde AS (
    SELECT
        time_key - time_key % 3600 AS stunde_key,
        avg(value_mw)              AS residual_mw
    FROM power
    WHERE series = 'Residual load'
    GROUP BY time_key - time_key % 3600
)
SELECT
    r.residual_mw,
    p.price_eur_mwh
FROM residual_stunde r
INNER JOIN price p ON p.time_key = r.stunde_key
"""


def stil(ax) -> None:
    ax.grid(axis="y", color=RASTER, linewidth=0.8)
    ax.set_axisbelow(True)
    for seite in ("top", "right"):
        ax.spines[seite].set_visible(False)
    for seite in ("left", "bottom"):
        ax.spines[seite].set_color(TEXT_LEISE)
    ax.tick_params(colors=TEXT_LEISE, labelsize=9)


def tagesprofil(con) -> Path:
    df = con.sql(SQL_TAGESPROFIL).df()

    # Zwei Felder übereinander mit gemeinsamer Stundenachse. Beide sind in MW, aber
    # die Last ist rund zehnmal größer als Solar: auf einer gemeinsamen y-Achse wäre
    # der Verlauf von Solar kaum zu erkennen.
    fig, (ax_last, ax_solar) = plt.subplots(
        2, 1, figsize=(8, 6), sharex=True, gridspec_kw={"hspace": 0.35}
    )

    for ax, spalte, farbe, titel in (
        (ax_last, "last_mw", BLAU, "Last"),
        (ax_solar, "solar_mw", ORANGE, "Solar"),
    ):
        ax.plot(df["stunde"], df[spalte], color=farbe, linewidth=2, marker="o", markersize=4)
        ax.set_title(titel, loc="left", fontsize=11, color=TEXT, fontweight="bold")
        ax.set_ylabel("Mittlere Leistung in MW", fontsize=9, color=TEXT_LEISE)
        stil(ax)

    ax_solar.set_ylim(bottom=0)
    ax_solar.set_xticks(range(0, 24, 3))
    ax_solar.set_xlabel("Ortsstunde (Beginn des Intervalls)", fontsize=9, color=TEXT_LEISE)
    ax_solar.set_xlim(-0.5, 23.5)

    fig.suptitle(
        "Mittleres Tagesprofil, Österreich", x=0.125, ha="left", fontsize=13, color=TEXT
    )

    ziel = FIG_DIR / "tagesprofil.png"
    fig.savefig(ziel, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return ziel


def preis_residuallast(con) -> Path:
    df = con.sql(SQL_PREIS_RESIDUALLAST).df()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        df["residual_mw"],
        df["price_eur_mwh"],
        s=14,
        color=BLAU,
        alpha=0.6,
        edgecolors="white",
        linewidths=0.4,
    )
    ax.axhline(0, color=TEXT_LEISE, linewidth=0.8)  # Nulllinie: negative Preise sind möglich

    ax.set_xlabel("Residuallast in MW (Last minus Wind minus Solar)", fontsize=9, color=TEXT_LEISE)
    ax.set_ylabel("Day-Ahead-Preis in EUR/MWh", fontsize=9, color=TEXT_LEISE)
    ax.set_title(
        f"Preis gegen Residuallast, {len(df)} Stunden",
        loc="left",
        fontsize=13,
        color=TEXT,
    )
    stil(ax)
    ax.grid(axis="x", color=RASTER, linewidth=0.8)

    ziel = FIG_DIR / "preis_residuallast.png"
    fig.savefig(ziel, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return ziel


def main() -> None:
    FIG_DIR.mkdir(exist_ok=True)
    with duckdb.connect(DB_PATH, read_only=True) as con:
        for ziel in (tagesprofil(con), preis_residuallast(con)):
            print(f"gespeichert: {ziel}")


if __name__ == "__main__":
    main()
