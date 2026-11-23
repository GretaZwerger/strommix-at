-- Mittleres Profil von Last und Solar gruppiert nach Stunde
WITH stunden as (
    SELECT
        hour(ts_local) AS stunde,
        avg(value_mw) FILTER (WHERE series = 'Load')  AS last_mw,
        avg(value_mw) FILTER (WHERE series = 'Solar') AS solar_mw
    FROM power
    WHERE 
        series IN ('Load', 'Solar')
    GROUP BY hour(ts_local)
)
SELECT 
    stunde,
    ROUND(last_mw, 2) as "Last in MW",
    ROUND(solar_mw, 2) as "Solar in MW"
FROM stunden
ORDER BY stunde