USE `flytau`;

SELECT f.aircraft_id_number, f.activity_year, f.activity_month,
	(SELECT COUNT(*) 
     FROM flight AS f1 
     WHERE f1.aircraft_id_number = f.aircraft_id_number 
     AND f1.status = 'ACTIVE'
     AND YEAR(f1.departure_datetime) = f.activity_year
     AND MONTH(f1.departure_datetime) = f.activity_month) AS active_flights,
	(SELECT COUNT(*) 
     FROM flight AS f2 
     WHERE f2.aircraft_id_number = f.aircraft_id_number 
     AND f2.status = 'CANCELED'
     AND YEAR(f2.departure_datetime) = f.activity_year
     AND MONTH(f2.departure_datetime) = f.activity_month) AS canceled_flights,
	((SELECT COUNT(DISTINCT DATE(f3.departure_datetime)) 
      FROM flight AS f3
      WHERE f3.aircraft_id_number = f.aircraft_id_number 
      AND f3.status = 'ACTIVE'
      AND YEAR(f3.departure_datetime) = f.activity_year
      AND MONTH(f3.departure_datetime) = f.activity_month) / 30 * 100) AS utilization,
    f_routes.origin_airport,
    f_routes.destination_airport
FROM (SELECT DISTINCT aircraft_id_number, YEAR(departure_datetime) AS activity_year, MONTH(departure_datetime) AS activity_month
	  FROM flight) AS f
LEFT JOIN (SELECT aircraft_id_number, YEAR(departure_datetime) AS r_year, MONTH(departure_datetime) AS r_month,
			origin_airport, destination_airport, COUNT(*) AS route_count
			FROM flight
			WHERE status = 'ACTIVE'
			GROUP BY aircraft_id_number, YEAR(departure_datetime), MONTH(departure_datetime), 
					 origin_airport, destination_airport) AS f_routes ON f.aircraft_id_number = f_routes.aircraft_id_number 
              AND f.activity_year = f_routes.r_year 
              AND f.activity_month = f_routes.r_month
              AND f_routes.route_count = (SELECT COUNT(*) AS max_cnt
										  FROM flight AS f_max
										  WHERE f_max.aircraft_id_number = f_routes.aircraft_id_number
										  AND f_max.status = 'ACTIVE'
										  AND YEAR(f_max.departure_datetime) = f_routes.r_year
										  AND MONTH(f_max.departure_datetime) = f_routes.r_month
										  GROUP BY f_max.origin_airport, f_max.destination_airport
										  ORDER BY max_cnt DESC
										  LIMIT 1)
ORDER BY f.aircraft_id_number ASC, f.activity_year ASC, f.activity_month ASC;