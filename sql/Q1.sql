USE `flytau`;

SELECT AVG(100.0 * (CASE WHEN booked.booked_seats IS NULL THEN 0 ELSE booked.booked_seats END) / ac_seat.total_seats) AS avg_occupancy_percent
FROM
  (SELECT flight_number, aircraft_id_number
	FROM flight
    WHERE departure_datetime < NOW()  AND status = 'ACTIVE') AS past_flights 
	JOIN (SELECT aircraft_id_number, COUNT(*) AS total_seats
		  FROM seat
		  GROUP BY aircraft_id_number) AS ac_seat ON ac_seat.aircraft_id_number = past_flights.aircraft_id_number 
          LEFT JOIN (SELECT r.flight_number, COUNT(*) AS booked_seats
					 FROM reservations AS r
					 JOIN seats_in_reservation as sir ON sir.reservation_code = r.reservation_code
					 WHERE r.reservations_status = 'ACTIVE'
					 GROUP BY r.flight_number) AS booked ON booked.flight_number = past_flights.flight_number;
