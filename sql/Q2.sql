USE `flytau`;

SELECT combos.aircraft_size,combos.aircraft_manufacturer, combos.class_type,
  SUM(CASE WHEN sif.price IS NULL THEN 0 ELSE sif.price END) AS total_revenue
FROM (SELECT DISTINCT a.size AS aircraft_size, a.manufacturer AS aircraft_manufacturer, c.type AS class_type, f.flight_number
    FROM flight AS f
    JOIN aircraft AS a ON f.aircraft_id_number = a.aircraft_id_number
    JOIN class AS c ON c.aircraft_id_number = a.aircraft_id_number) AS combos
LEFT JOIN reservations AS r ON r.flight_number = combos.flight_number
LEFT JOIN seats_in_reservation AS sir ON sir.reservation_code = r.reservation_code
LEFT JOIN seats_in_flights AS sif ON sif.flight_number = combos.flight_number
 AND sif.aircraft_id_number = sir.aircraft_id_number
 AND sif.class_type = sir.class_type
 AND sif.row_number = sir.row_number
 AND sif.column_number = sir.column_number
GROUP BY combos.aircraft_size, combos.aircraft_manufacturer, combos.class_type
ORDER BY combos.aircraft_size, combos.aircraft_manufacturer, combos.class_type;