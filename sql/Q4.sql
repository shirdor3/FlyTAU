USE `flytau`;


SELECT YEAR(r.reservation_date) AS order_year, MONTH(r.reservation_date) AS order_month,
    (SUM(CASE WHEN r.reservations_status = 'CUSTOMER_CANCELED' THEN 1 
    ELSE 0 END) / COUNT(reservation_code) * 100) AS cancellation_rate

FROM reservations AS r
GROUP BY YEAR(r.reservation_date), MONTH(r.reservation_date)
ORDER BY order_year ASC, order_month ASC;