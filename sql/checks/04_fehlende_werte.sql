-- Liefert pro Reihe die Anzahl fehlender Messwerte.
SELECT
    series,
    count(*) AS fehlende_werte
FROM power
WHERE value_mw IS NULL
GROUP BY series
ORDER BY fehlende_werte DESC