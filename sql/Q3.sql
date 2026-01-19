USE `flytau`;

SELECT staff_id, first_name, last_name,
	SUM(CASE WHEN flight_duration < 360 THEN flight_duration ELSE 0 END) / 60.0 AS short_flights_hours,
    SUM(CASE WHEN flight_duration >= 360 THEN flight_duration ELSE 0 END) / 60.0 AS long_flights_hours,
    SUM(flight_duration) / 60.0 AS total_hours
FROM (SELECT p.id_number AS staff_id, p.first_name, p.last_name, fr.flight_duration
	  FROM pilot AS p
      JOIN pilots_on_flights AS pof ON p.id_number = pof.id_number
      JOIN flight AS f ON pof.flight_number = f.flight_number
      JOIN flight_route AS fr ON f.origin_airport = fr.origin_airport AND f.destination_airport = fr.destination_airport
      WHERE f.status = 'ACTIVE' AND f.departure_datetime < datetime('now')
    UNION ALL
    SELECT fa.id_number AS staff_id, fa.first_name, fa.last_name, fr.flight_duration
    FROM flight_attendant AS fa
    JOIN flight_attendants_on_flights AS faof ON fa.id_number = faof.id_number
    JOIN flight AS f ON faof.flight_number = f.flight_number
    JOIN flight_route AS fr ON f.origin_airport = fr.origin_airport AND f.destination_airport = fr.destination_airport
    WHERE f.status = 'ACTIVE' AND f.departure_datetime < datetime('now')) AS all_staff
GROUP BY staff_id, first_name, last_name
ORDER BY total_hours DESC;