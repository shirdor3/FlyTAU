import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils import db_conn


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "static", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _query_df(sql: str, params=None) -> pd.DataFrame:
    if params is None:
        params = []

    with db_conn() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

        # Handle case where query returns no results
        if not rows:
            return pd.DataFrame()

        # Extract column names from the cursor description
        # This is required because simple pd.DataFrame(rows) won't get headers from sqlite3
        columns = [description[0] for description in cur.description]

    return pd.DataFrame(rows, columns=columns)

def _save_plot(fig, filename: str) -> str:
    path = os.path.join(REPORTS_DIR, filename)
    fig.tight_layout()
    fig.savefig(path, dpi=160, transparent=False)
    plt.close(fig)
    return f"reports/{filename}"


def report_avg_occupancy():
    sql = """
    SELECT AVG(100.0 * (CASE WHEN booked.booked_seats IS NULL THEN 0 ELSE booked.booked_seats END) / ac_seat.total_seats) AS avg_occupancy_percent
    FROM
      (SELECT flight_number, aircraft_id_number
        FROM flight
        WHERE departure_datetime < datetime('now')  AND status = 'ACTIVE') AS past_flights
        JOIN (SELECT aircraft_id_number, COUNT(*) AS total_seats
              FROM seat
              GROUP BY aircraft_id_number) AS ac_seat ON ac_seat.aircraft_id_number = past_flights.aircraft_id_number
              LEFT JOIN (SELECT r.flight_number, COUNT(*) AS booked_seats
                         FROM reservations AS r
                         JOIN seats_in_reservation as sir ON sir.reservation_code = r.reservation_code
                         WHERE r.reservations_status = 'ACTIVE'
                         GROUP BY r.flight_number) AS booked ON booked.flight_number = past_flights.flight_number;
    """
    df = _query_df(sql)
    try:
        val = float(df.iloc[0])
    except:
        val = 0

    img = None

    table_df = pd.DataFrame([{
        "metric": "Average occupancy (past flights)",
        "value": round(val, 2),
        "unit": "%"
    }])

    return img, table_df


def report_revenue_by_combo():
    sql = """
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
    """
    df = _query_df(sql)
    if df.empty:
        fig = plt.figure()
        plt.title("Revenue by Combo (no data)")
        img = _save_plot(fig, "report2_revenue_combo.png")
        return img, df

    df["label"] = df["aircraft_size"] + " | " + df["aircraft_manufacturer"] + " | " + df["class_type"]
    df["total_revenue"] = pd.to_numeric(df["total_revenue"]).fillna(0)

    fig = plt.figure(figsize=(10, 4))
    plt.title("Revenue by Aircraft Size / Manufacturer / Class")
    plt.bar(df["label"], df["total_revenue"])
    plt.ylabel("Revenue")
    plt.xticks(rotation=30, ha="right")

    img = _save_plot(fig, "report2_revenue_combo.png")
    return img, df



def report_staff_hours():
    sql = """
    SELECT staff_id, first_name, last_name,
        SUM(CASE WHEN flight_duration < 360 THEN flight_duration ELSE 0 END) / 60.0 AS short_hours,
        SUM(CASE WHEN flight_duration >= 360 THEN flight_duration ELSE 0 END) / 60.0 AS long_hours,
        SUM(flight_duration) / 60.0 AS total_hours
    FROM (
        SELECT p.id_number AS staff_id, p.first_name, p.last_name, fr.flight_duration
        FROM pilot AS p
        JOIN pilots_on_flights AS pof ON p.id_number = pof.id_number
        JOIN flight AS f ON pof.flight_number = f.flight_number
        JOIN flight_route AS fr 
          ON f.origin_airport = fr.origin_airport 
         AND f.destination_airport = fr.destination_airport
        WHERE f.status = 'ACTIVE' AND f.departure_datetime < datetime('now')

        UNION ALL

        SELECT fa.id_number AS staff_id, fa.first_name, fa.last_name, fr.flight_duration
        FROM flight_attendant AS fa
        JOIN flight_attendants_on_flights AS faof ON fa.id_number = faof.id_number
        JOIN flight AS f ON faof.flight_number = f.flight_number
        JOIN flight_route AS fr 
          ON f.origin_airport = fr.origin_airport 
         AND f.destination_airport = fr.destination_airport
        WHERE f.status = 'ACTIVE' AND f.departure_datetime < datetime('now')
    ) AS all_staff
    GROUP BY staff_id, first_name, last_name
    ORDER BY total_hours DESC;
    """

    df = _query_df(sql)
    if df.empty:
        fig = plt.figure()
        plt.title("No staff flight data")
        img = _save_plot(fig, "report3_staff_hours.png")
        return img, df

    df["name"] = df["first_name"] + " " + df["last_name"]

    for c in ["short_hours", "long_hours", "total_hours"]:
        df[c] = pd.to_numeric(df[c]).fillna(0).round(2)

    top10 = df.head(10)

    fig = plt.figure(figsize=(10, 5))
    plt.title("Top 10 Staff Members by Total Flight Hours")

    plt.bar(top10["name"], top10["short_hours"], label="short flights")
    plt.bar(
        top10["name"],
        top10["long_hours"],
        bottom=top10["short_hours"],
        label="long flights"
    )

    plt.ylabel("Flight Hours")
    plt.xticks(rotation=30, ha="right")
    plt.legend()

    img = _save_plot(fig, "report3_staff_hours.png")

    table_df = df[[
        "name",
        "short_hours",
        "long_hours",
        "total_hours"
    ]].rename(columns={
        "name": "שם עובד",
        "short_hours": "שעות בטיסות קצרות",
        "long_hours": "שעות בטיסות ארוכות",
        "total_hours": "סה״כ שעות טיסה"
    })

    return img, table_df



def report_cancellation_rate():
    sql = """
    SELECT 
    CAST(strftime('%Y', r.reservation_date) AS INTEGER) AS order_year, 
    CAST(strftime('%m', r.reservation_date) AS INTEGER) AS order_month,
    (SUM(CASE WHEN r.reservations_status = 'CUSTOMER_CANCELED' THEN 1 ELSE 0 END) * 100.0 / COUNT(reservation_code)) AS cancellation_rate
    FROM reservations AS r
    GROUP BY order_year, order_month
    ORDER BY order_year ASC, order_month ASC;
    """
    df = _query_df(sql)
    if df.empty:
        fig = plt.figure()
        plt.title("Cancellation Rate (no data)")
        img = _save_plot(fig, "report4_cancellation_rate.png")
        return img, df

    df["label"] = df["order_year"].astype(str) + "-" + df["order_month"].astype(int).astype(str).str.zfill(2)
    df["cancellation_rate"] = pd.to_numeric(df["cancellation_rate"]).fillna(0)

    fig = plt.figure(figsize=(10, 4))
    plt.title("Cancellation Rate by Month")
    plt.bar(df["label"], df["cancellation_rate"])
    plt.ylabel("Cancellation Rate (%)")
    plt.xticks(rotation=30, ha="right")
    plt.ylim(0, max(5, df["cancellation_rate"].max() + 5))

    for i, v in enumerate(df["cancellation_rate"]):
        plt.text(i, v + 0.2, f"{v:.1f}%", ha="center", va="bottom", fontsize=9)

    img = _save_plot(fig, "report4_cancellation_rate.png")
    return img, df


def report_aircraft_monthly_summary():
    sql = """
    SELECT 
    f.aircraft_id_number, 
    f.activity_year, 
    f.activity_month,
    
    -- 1. Active Flights Count
    (SELECT COUNT(*)
     FROM flight AS f1
     WHERE f1.aircraft_id_number = f.aircraft_id_number
     AND f1.status = 'ACTIVE'
     AND CAST(strftime('%Y', f1.departure_datetime) AS INTEGER) = f.activity_year
     AND CAST(strftime('%m', f1.departure_datetime) AS INTEGER) = f.activity_month) AS active_flights,

    -- 2. Canceled Flights Count
    (SELECT COUNT(*)
     FROM flight AS f2
     WHERE f2.aircraft_id_number = f.aircraft_id_number
     AND f2.status = 'CANCELED'
     AND CAST(strftime('%Y', f2.departure_datetime) AS INTEGER) = f.activity_year
     AND CAST(strftime('%m', f2.departure_datetime) AS INTEGER) = f.activity_month) AS canceled_flights,

    -- 3. Utilization (Rounded to 2 decimals)
    ROUND(
        (SELECT COUNT(DISTINCT date(f3.departure_datetime))
         FROM flight AS f3
         WHERE f3.aircraft_id_number = f.aircraft_id_number
         AND f3.status = 'ACTIVE'
         AND CAST(strftime('%Y', f3.departure_datetime) AS INTEGER) = f.activity_year
         AND CAST(strftime('%m', f3.departure_datetime) AS INTEGER) = f.activity_month
        ) / 30.0 * 100
    , 2) AS utilization,

    f_routes.origin_airport,
    f_routes.destination_airport

FROM (
    -- Main Subquery: Get unique Aircraft-Year-Month combos
    SELECT DISTINCT 
        aircraft_id_number, 
        CAST(strftime('%Y', departure_datetime) AS INTEGER) AS activity_year, 
        CAST(strftime('%m', departure_datetime) AS INTEGER) AS activity_month
    FROM flight
) AS f

LEFT JOIN (
    -- Route Stats Subquery
    SELECT 
        aircraft_id_number, 
        CAST(strftime('%Y', departure_datetime) AS INTEGER) AS r_year, 
        CAST(strftime('%m', departure_datetime) AS INTEGER) AS r_month,
        origin_airport, 
        destination_airport, 
        COUNT(*) AS route_count
    FROM flight
    WHERE status = 'ACTIVE'
    GROUP BY aircraft_id_number, r_year, r_month, origin_airport, destination_airport
) AS f_routes 
  ON f.aircraft_id_number = f_routes.aircraft_id_number
  AND f.activity_year = f_routes.r_year
  AND f.activity_month = f_routes.r_month
  AND f_routes.route_count = (
      -- Max Count Subquery
      SELECT COUNT(*) AS max_cnt
      FROM flight AS f_max
      WHERE f_max.aircraft_id_number = f_routes.aircraft_id_number
      AND f_max.status = 'ACTIVE'
      AND CAST(strftime('%Y', f_max.departure_datetime) AS INTEGER) = f_routes.r_year
      AND CAST(strftime('%m', f_max.departure_datetime) AS INTEGER) = f_routes.r_month
      GROUP BY f_max.origin_airport, f_max.destination_airport
      ORDER BY max_cnt DESC
      LIMIT 1
  )

ORDER BY f.aircraft_id_number ASC, f.activity_year ASC, f.activity_month ASC;
    """
    df = _query_df(sql)
    if df.empty:
        fig = plt.figure()
        plt.title("Aircraft Monthly Summary (no data)")
        img = _save_plot(fig, "report5_aircraft_summary.png")
        return img, df

    df["label"] = (
        df["aircraft_id_number"].astype(str)
        + " | "
        + df["activity_year"].astype(str)
        + "-"
        + df["activity_month"].astype(int).astype(str).str.zfill(2)
    )
    df["utilization"] = pd.to_numeric(df["utilization"]).fillna(0)

    fig = plt.figure(figsize=(10, 4))
    plt.title("Aircraft Utilization by Month (assume 30 days)")
    plt.bar(df["label"], df["utilization"])
    plt.ylabel("Utilization %")
    plt.xticks(rotation=30, ha="right")
    plt.ylim(0, 100)

    img = _save_plot(fig, "report5_aircraft_summary.png")
    return img, df