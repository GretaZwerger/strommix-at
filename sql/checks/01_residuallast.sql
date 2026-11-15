-- Eigene Residuallast (Last - Wind - Solar) gegen die Reihe des Anbieters.
-- Liefert die Zeitpunkte, an denen beide um mehr als 0,01 MW abweichen
-- oder an denen einer der vier Werte fehlt.
WITH je_zeitpunkt AS (
    SELECT
        time_key,
        max(value_mw) FILTER (WHERE series = 'Load')          AS last_mw,
        max(value_mw) FILTER (WHERE series = 'Wind onshore')  AS wind_mw,
        max(value_mw) FILTER (WHERE series = 'Solar')         AS solar_mw,
        max(value_mw) FILTER (WHERE series = 'Residual load') AS residual_anbieter_mw
    FROM power
    GROUP BY time_key
)
SELECT
    time_key,
    last_mw - wind_mw - solar_mw AS residual_eigen_mw,
    residual_anbieter_mw
FROM je_zeitpunkt
-- Fehlt ein Wert, ist der Vergleich NULL und die Zeile fiele ohne coalesce stillschweigend durch.
WHERE NOT coalesce(abs(last_mw - wind_mw - solar_mw - residual_anbieter_mw) <= 0.01, false)
