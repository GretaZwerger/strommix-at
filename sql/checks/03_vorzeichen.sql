-- Liefert Messwerte mit physikalisch unmöglichem Vorzeichen.
SELECT
    p.series,
    sc.category,
    p.time_key,
    p.ts_local,
    p.value_mw
FROM power p
INNER JOIN series_category sc ON p.series = sc.series
WHERE (sc.category = 'erzeugung' AND p.value_mw < 0)
   OR (p.series = 'Hydro pumped storage' AND p.value_mw < 0)
   OR (p.series = 'Hydro pumped storage consumption' AND p.value_mw > 0)
   OR (p.series = 'Load' AND p.value_mw <= 0)