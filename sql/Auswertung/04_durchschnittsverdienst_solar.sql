-- Marktwert von Solarstrom im Vergleich zum Durchschnittspreis.
WITH solar_stunde AS (
    -- time_key % 3600 sind die Sekunden seit Beginn der Stunde
    SELECT
        time_key - time_key % 3600 AS stunde_key,
        avg(value_mw)              AS solar_mw
    FROM power
    WHERE series = 'Solar'
    GROUP BY time_key - time_key % 3600
)
SELECT
    count(*)                                                        AS "Stunden",
    round(avg(p.price_eur_mwh), 2)                                  AS "Durchschnittspreis in EUR/MWh",
    round(sum(s.solar_mw * p.price_eur_mwh) / sum(s.solar_mw), 2)   AS "Marktwert Solar in EUR/MWh",
    round(sum(s.solar_mw * p.price_eur_mwh) / sum(s.solar_mw) / avg(p.price_eur_mwh), 2) AS "Wertfaktor" -- Wieviel erzeugt Solar vom Durchschnitt?
FROM solar_stunde s
INNER JOIN price p ON p.time_key = s.stunde_key