-- Energie je Erzeugungsart und ihr Anteil an der gesamten Erzeugung (gerundet).
WITH sums AS (
    SELECT
        p.series,
        sum(p.value_mw) AS sum_series
    FROM power p
    INNER JOIN series_category sc ON p.series = sc.series
    WHERE sc.category = 'erzeugung'
    GROUP BY p.series
)
SELECT
    series AS "Quelle",
    ROUND(sum_series * 0.25, 2) AS "Energie in MWh",
    ROUND(sum_series / sum(sum_series) OVER () * 100, 2) AS "Anteil in Prozent"
FROM sums
ORDER BY sum_series DESC