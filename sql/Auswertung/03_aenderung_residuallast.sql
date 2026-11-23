-- Die zehn steilsten Änderungen der Residuallast zwischen zwei Viertelstunden.
WITH last_values as (
    SELECT 
        ts_local,
        time_key,
        value_mw,
        lag(value_mw) OVER(ORDER BY time_key) as value_mw_before
    from power
    WHERE series = 'Residual load'
)
SELECT
    ts_local as "Lokale Zeit",
    value_mw as "Residuallast in MW",
    ROUND(value_mw - value_mw_before, 2) as "Änderung in MW"
from last_values
WHERE value_mw_before IS NOT NULL
ORDER BY abs(value_mw - value_mw_before) DESC LIMIT 10