-- Pumpspeicher: Wird billig gepumpt und teuer erzeugt?
WITH speicher_stunde AS (
    SELECT
        time_key - time_key % 3600                                                AS stunde_key,
        -avg(value_mw) FILTER (WHERE series = 'Hydro pumped storage consumption') AS pumpen_mw, -- Der Pumpbetrieb ist negativ geliefert; das Minus macht daraus einen positiven Verbrauch.
         avg(value_mw) FILTER (WHERE series = 'Hydro pumped storage')             AS erzeugen_mw
    FROM power
    WHERE series IN ('Hydro pumped storage', 'Hydro pumped storage consumption') 
    GROUP BY time_key - time_key % 3600
)
SELECT
    round(sum(s.pumpen_mw))                                     AS "Gepumpt in MWh",
    round(sum(s.erzeugen_mw))                                   AS "Erzeugt in MWh",
    round(sum(s.pumpen_mw * p.price_eur_mwh)
          / sum(s.pumpen_mw), 2)                                AS "Preis beim Pumpen in EUR/MWh",
    round(sum(s.erzeugen_mw * p.price_eur_mwh)
          / sum(s.erzeugen_mw), 2)                              AS "Preis beim Erzeugen in EUR/MWh",
    round(sum(s.erzeugen_mw) / sum(s.pumpen_mw), 2)             AS "Verhältnis erzeugt zu gepumpt"
FROM speicher_stunde s
INNER JOIN price p ON p.time_key = s.stunde_key