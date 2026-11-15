-- Liefert die Stellen, an denen der nächste Zeitpunkt einer Reihe
-- nicht genau 900 Sekunden später liegt.
WITH nachfolger AS (
    SELECT
        series,
        time_key,
        lead(time_key) OVER (PARTITION BY series ORDER BY time_key) AS next_time_key
    FROM power
)
SELECT
    series,
    time_key,
    next_time_key,
    next_time_key - time_key AS abstand_s
FROM nachfolger
WHERE next_time_key IS NOT NULL          -- letzte Zeile jeder Reihe hat keinen Nachfolger
  AND next_time_key - time_key <> 900