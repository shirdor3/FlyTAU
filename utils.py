import sqlite3
from contextlib import contextmanager
import random
from datetime import date

DB_PATH = 'FlyTAU_db.db'
@contextmanager
def db_conn():
    mydb = None
    cursor = None
    try:
        mydb = sqlite3.connect(
            DB_PATH,
            check_same_thread=False
        )
        mydb.isolation_level = None
        mydb.row_factory = sqlite3.Row
        cursor = mydb.cursor()
        yield cursor
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()


@contextmanager
def db_tx():
    mydb = None
    cursor = None
    try:
        mydb = sqlite3.connect(
            DB_PATH,
            check_same_thread=False
        )
        mydb.isolation_level = None
        mydb.row_factory = sqlite3.Row
        cursor = mydb.cursor()
        yield mydb, cursor
        mydb.commit()
    except:
        if mydb:
            mydb.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()


def get_active_reservations_for_guest(email: str, reservation_code: int):
    sql = """
    SELECT
      r.reservation_code,
      r.reservations_status,
      r.reservation_date,
      r.total_payment,
      r.email,
      r.flight_number,
      f.origin_airport,
      f.destination_airport,
      f.departure_datetime,
      f.status AS flight_status
    FROM reservations r
    JOIN flight f ON f.flight_number = r.flight_number
    WHERE r.email = ?
      AND r.reservation_code = ?
      AND r.reservations_status = 'ACTIVE'
      AND f.status = 'ACTIVE'
      AND f.departure_datetime > datetime('now')
    ORDER BY f.departure_datetime ASC;
    """
    with db_conn() as cur:
        cur.execute(sql, (email, reservation_code))
        return cur.fetchall()

def cancel_reservation_for_guest(email: str, reservation_code: int) -> bool:
    sql = """
    UPDATE reservations
    SET reservations_status = 'CUSTOMER_CANCELED'
    WHERE email = ?
      AND reservation_code = ?
      AND reservations_status = 'ACTIVE';
    """
    with db_conn() as cur:
        cur.execute(sql, (email, reservation_code))
        return cur.rowcount == 1


def get_seats_for_aircraft_class(aircraft_id_number: int, class_type: str):
    sql = (
        "SELECT `aircraft_id_number`, `class_type`, `row_number`, `column_number`, `price` "
        "FROM `seats_in_flights` "
        "WHERE `aircraft_id_number` = ? AND `class_type` = ? "
        "ORDER BY `row_number`, `column_number`"
    )

    with db_conn() as cur:
        cur.execute(sql, (aircraft_id_number, class_type))
        return cur.fetchall()


def get_all_flights_with_hours():
    sql = """
    SELECT
  flight_number,
  aircraft_id_number,
  origin_airport,
  destination_airport,
  departure_datetime,
  status,
  CAST((julianday(departure_datetime) - julianday('now')) * 24 AS INTEGER) AS hours_to_departure
FROM flight
ORDER BY departure_datetime;
    """
    with db_conn() as cur:
        cur.execute(sql)
        return cur.fetchall()


def cancel_flight_and_linked_reservations(flight_number: int) -> dict:
    with db_tx() as (conn, cur):
        sql_cancel_flight = """
            UPDATE flight
            SET status = 'CANCELED'
            WHERE flight_number = ?
              AND status = 'ACTIVE'
              AND departure_datetime > datetime('now', '+72 hours');
        """
        cur.execute(sql_cancel_flight, (flight_number,))

        if cur.rowcount != 1:
            sql_info = """
            SELECT status,
                   departure_datetime,
                   CAST((julianday(departure_datetime) - julianday('now')) * 24 AS INTEGER) AS hours_to_departure
            FROM flight
            WHERE flight_number = ?;
            """
            cur.execute(sql_info, (flight_number,))
            info = cur.fetchone()

            if not info:
                return {"ok": False, "reason": "NOT_FOUND"}

            if info["status"] != "ACTIVE":
                return {"ok": False, "reason": "ALREADY_CANCELED", "info": info}

            return {"ok": False, "reason": "TOO_SOON", "info": info}

        sql_cancel_res = """
        UPDATE reservations
        SET reservations_status = 'SYSTEM_CANCELED',
            total_payment = 0
        WHERE flight_number = ?
          AND reservations_status = 'ACTIVE';
        """
        cur.execute(sql_cancel_res, (flight_number,))
        reservations_updated = cur.rowcount

        return {"ok": True, "flight_number": flight_number, "reservations_updated": reservations_updated}


def get_route_origins():
    sql = "SELECT DISTINCT origin_airport FROM flight_route ORDER BY origin_airport;"
    with db_conn() as cur:
        cur.execute(sql)
        return [r["origin_airport"] for r in cur.fetchall()]


def get_route_destinations(origin_airport: str):
    sql = """
    SELECT destination_airport
    FROM flight_route
    WHERE origin_airport = ?
    ORDER BY destination_airport;
    """
    with db_conn() as cur:
        cur.execute(sql, (origin_airport,))
        return [r["destination_airport"] for r in cur.fetchall()]


def get_flight_duration_minutes(origin_airport: str, destination_airport: str):
    sql = """
    SELECT flight_duration
    FROM flight_route
    WHERE origin_airport = ? AND destination_airport = ?;
    """
    with db_conn() as cur:
        cur.execute(sql, (origin_airport, destination_airport))
        row = cur.fetchone()
        return None if not row else row["flight_duration"]


def is_long_flight(duration_minutes: int) -> bool:
    return duration_minutes is not None and duration_minutes >= 360


def get_available_aircraft(departure_dt, arrival_dt, origin_airport: str, long_required: bool):

    sql = """
    SELECT a.aircraft_id_number, a.size, a.manufacturer
FROM aircraft a
WHERE (? = 0 OR a.size = 'LARGE')

  -- 1. Exclude aircraft that are busy during the requested window
  AND a.aircraft_id_number NOT IN (
    SELECT f.aircraft_id_number
    FROM flight f
    JOIN flight_route fr
      ON fr.origin_airport = f.origin_airport
     AND fr.destination_airport = f.destination_airport
    WHERE f.status = 'ACTIVE'
      AND f.aircraft_id_number IS NOT NULL
      AND (
        f.departure_datetime < ?  -- Overlap Start
        -- SQLite Dynamic Interval: Adds flight_duration minutes to departure
        AND datetime(f.departure_datetime, '+' || fr.flight_duration || ' minutes') > ? -- Overlap End
      )
  )

  -- 2. Ensure aircraft is at the correct starting airport
  AND (
    (
      -- Logic: Find the destination of the LAST flight that landed before our new flight departs
      (
        SELECT f2.destination_airport
        FROM flight f2
        JOIN flight_route fr2
          ON fr2.origin_airport = f2.origin_airport
         AND fr2.destination_airport = f2.destination_airport
        WHERE f2.aircraft_id_number = a.aircraft_id_number
          AND f2.status <> 'CANCELED'
          AND datetime(f2.departure_datetime, '+' || fr2.flight_duration || ' minutes') <= ?
        ORDER BY datetime(f2.departure_datetime, '+' || fr2.flight_duration || ' minutes') DESC
        LIMIT 1
      ) = ?
    )
    OR
    (
      -- Logic: If the aircraft has NEVER flown, assume it is at 'TLV'
      ? = 'TLV'
      AND NOT EXISTS (
        SELECT 1
        FROM flight f0
        WHERE f0.aircraft_id_number = a.aircraft_id_number
          AND f0.status <> 'CANCELED'
          AND f0.departure_datetime IS NOT NULL
      )
    )
  )

ORDER BY a.aircraft_id_number;
    """

    with db_conn() as cur:
        cur.execute(sql, (
            1 if long_required else 0,
            arrival_dt,
            departure_dt,
            departure_dt,
            origin_airport,
            origin_airport
        ))
        return cur.fetchall()

def required_crew_counts(aircraft_size: str):
    size = (aircraft_size or "").upper()
    if size == "LARGE":
        return {"pilots": 3, "attendants": 6}
    if size == "SMALL":
        return {"pilots": 2, "attendants": 3}
    return {"pilots": 2, "attendants": 2}

def get_available_pilots(departure_dt, arrival_dt, origin_airport: str, long_required: bool):
    sql = """
   SELECT p.id_number, p.first_name, p.last_name, p.long_flight_certification
FROM pilot p
WHERE (? = 0 OR p.long_flight_certification = 1)

  -- 1. Exclude pilots who are currently flying during the window
  AND p.id_number NOT IN (
    SELECT pf.id_number
    FROM pilots_on_flights pf
    JOIN flight f ON f.flight_number = pf.flight_number
    JOIN flight_route fr
      ON fr.origin_airport = f.origin_airport
     AND fr.destination_airport = f.destination_airport
    WHERE f.status = 'ACTIVE'
      AND (
        f.departure_datetime < ? -- Overlap Start
        -- SQLite Dynamic Interval: Add duration minutes to departure
        AND datetime(f.departure_datetime, '+' || fr.flight_duration || ' minutes') > ? -- Overlap End
      )
  )
  AND (
    (
      -- 2a. Check pilot's last known location
      (
        SELECT f2.destination_airport
        FROM pilots_on_flights pf2
        JOIN flight f2 ON f2.flight_number = pf2.flight_number
        JOIN flight_route fr2
          ON fr2.origin_airport = f2.origin_airport
         AND fr2.destination_airport = f2.destination_airport
        WHERE pf2.id_number = p.id_number
          AND f2.status <> 'CANCELED'
          AND datetime(f2.departure_datetime, '+' || fr2.flight_duration || ' minutes') <= ?
        ORDER BY datetime(f2.departure_datetime, '+' || fr2.flight_duration || ' minutes') DESC
        LIMIT 1
      ) = ?
    )
    OR
    (
      -- 2b. If pilot has never flown, assume they are at TLV
      ? = 'TLV'
      AND NOT EXISTS (
        SELECT 1
        FROM pilots_on_flights pf0
        JOIN flight f0 ON f0.flight_number = pf0.flight_number
        WHERE pf0.id_number = p.id_number
          AND f0.status <> 'CANCELED'
          AND f0.departure_datetime IS NOT NULL
      )
    )
  )

ORDER BY p.id_number;
    """
    with db_conn() as cur:
        cur.execute(sql, (
            1 if long_required else 0,
            arrival_dt,
            departure_dt,
            departure_dt,
            origin_airport,
            origin_airport
        ))
        return cur.fetchall()


def get_available_attendants(departure_dt, arrival_dt, origin_airport: str, long_required: bool):
    sql = """
    SELECT fa.id_number, fa.first_name, fa.last_name, fa.long_flight_certification
FROM flight_attendant fa
WHERE (? = 0 OR fa.long_flight_certification = 1)

  -- 1. Exclude flight attendants who are flying during the requested window
  AND fa.id_number NOT IN (
    SELECT ff.id_number
    FROM flight_attendants_on_flights ff
    JOIN flight f ON f.flight_number = ff.flight_number
    JOIN flight_route fr
      ON fr.origin_airport = f.origin_airport
     AND fr.destination_airport = f.destination_airport
    WHERE f.status = 'ACTIVE'
      AND (
        f.departure_datetime < ?
        -- SQLite Dynamic Interval
        AND datetime(f.departure_datetime, '+' || fr.flight_duration || ' minutes') > ?
      )
  )

  -- 2. Ensure flight attendant is at the correct airport
  AND (
    (
      -- Logic: Find destination of their last completed flight
      (
        SELECT f2.destination_airport
        FROM flight_attendants_on_flights ff2
        JOIN flight f2 ON f2.flight_number = ff2.flight_number
        JOIN flight_route fr2
          ON fr2.origin_airport = f2.origin_airport
         AND fr2.destination_airport = f2.destination_airport
        WHERE ff2.id_number = fa.id_number
          AND f2.status <> 'CANCELED'
          AND datetime(f2.departure_datetime, '+' || fr2.flight_duration || ' minutes') <= ?
        ORDER BY datetime(f2.departure_datetime, '+' || fr2.flight_duration || ' minutes') DESC
        LIMIT 1
      ) = ?
    )
    OR
    (
      -- Logic: If they have never flown, assume they are at 'TLV'
      ? = 'TLV'
      AND NOT EXISTS (
        SELECT 1
        FROM flight_attendants_on_flights ff0
        JOIN flight f0 ON f0.flight_number = ff0.flight_number
        WHERE ff0.id_number = fa.id_number
          AND f0.status <> 'CANCELED'
          AND f0.departure_datetime IS NOT NULL
      )
    )
  )

ORDER BY fa.id_number;
    """
    with db_conn() as cur:
        cur.execute(sql, (
            1 if long_required else 0,
            arrival_dt,
            departure_dt,
            departure_dt,
            origin_airport,
            origin_airport
        ))
        return cur.fetchall()
def get_aircraft_classes(aircraft_id_number: int):
    sql = """
    SELECT type
    FROM class
    WHERE aircraft_id_number = ?
    ORDER BY type;
    """
    with db_conn() as cur:
        cur.execute(sql, (aircraft_id_number,))
        return [r["type"] for r in cur.fetchall()]


def create_flight_with_crew_and_prices(
    flight_number: int,
    aircraft_id_number: int,
    origin_airport: str,
    destination_airport: str,
    departure_dt,
    pilots_ids: list[int],
    attendants_ids: list[int],
    class_prices: dict
):
    pilots_ids = [int(x) for x in pilots_ids if str(x).strip() != ""]
    attendants_ids = [int(x) for x in attendants_ids if str(x).strip() != ""]

    if len(pilots_ids) != len(set(pilots_ids)):
        raise ValueError("נבחר אותו טייס יותר מפעם אחת.")
    if len(attendants_ids) != len(set(attendants_ids)):
        raise ValueError("נבחר אותו דייל יותר מפעם אחת.")

    norm_prices = {}
    for k, v in (class_prices or {}).items():
        kk = (k or "").strip().upper()
        if kk:
            norm_prices[kk] = float(v)

    if "ECONOMY" not in norm_prices:
        raise ValueError("חובה לספק מחיר למחלקת ECONOMY.")

    with db_tx() as (conn, cur):
        cur.execute("SELECT 1 FROM flight WHERE flight_number=? LIMIT 1;", (flight_number,))
        if cur.fetchone():
            cur.fetchall()
            raise ValueError("מספר הטיסה כבר קיים במערכת.")
        cur.fetchall()

        cur.execute("""
            INSERT INTO flight
              (flight_number, aircraft_id_number, origin_airport, destination_airport, departure_datetime, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
        """, (flight_number, aircraft_id_number, origin_airport, destination_airport, departure_dt))

        for pid in pilots_ids:
            cur.execute("""
                INSERT INTO pilots_on_flights (id_number, flight_number)
                VALUES (?, ?)
            """, (pid, flight_number))

        for aid in attendants_ids:
            cur.execute("""
                INSERT INTO flight_attendants_on_flights (id_number, flight_number)
                VALUES (?, ?)
            """, (aid, flight_number))

        cur.execute("""
            SELECT aircraft_id_number, class_type, `row_number`, column_number
            FROM seat
            WHERE aircraft_id_number = ?
            ORDER BY class_type, `row_number`, column_number;
        """, (aircraft_id_number,))
        seats = cur.fetchall()

        if not seats:
            raise ValueError("אין מושבים מוגדרים למטוס הזה (seat table empty).")

        rows_to_insert = []
        for s in seats:
            ct = (s["class_type"] or "").strip().upper()
            if ct not in norm_prices:
                continue

            rows_to_insert.append((
                s["aircraft_id_number"],
                s["class_type"],
                s["row_number"],
                s["column_number"],
                flight_number,
                float(norm_prices[ct])
            ))

        if not rows_to_insert:
            raise ValueError("לא נמצא אף מושב להוספה לטיסה (בדוק מחירים).")

        cur.executemany("""
            INSERT INTO seats_in_flights
              (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, rows_to_insert)


def generate_unique_flight_number() -> int:

    for _ in range(20000):
        n = random.randint(0, 9999)
        with db_conn() as cur:
            cur.execute("SELECT 1 FROM flight WHERE flight_number = ? LIMIT 1;", (n,))
            exists = cur.fetchone() is not None
        if not exists:
            return n
    raise RuntimeError("לא ניתן להגריל מספר טיסה פנוי (ייתכן שכל הטווח תפוס).")


def authenticate_user(email, password):
    sql = """
    SELECT rc.email, c.first_name, c.last_name
    FROM registered_customer rc
    JOIN customer c ON rc.email = c.email
    WHERE rc.email = ? AND rc.password = ?;
    """
    with db_conn() as cur:
        cur.execute(sql, (email, password))
        return cur.fetchone()


def signup_user(data):
    email = data['email']
    passport = data['passport']

    with db_conn() as cur:
        cur.execute("SELECT email FROM customer WHERE email = ?", (email,))
        if cur.fetchone():
            cur.fetchall()
            return False, "האימייל כבר רשום במערכת"
        cur.fetchall()

        cur.execute("SELECT email FROM registered_customer WHERE passport_number = ?", (passport,))
        if cur.fetchone():
            cur.fetchall()
            return False, "שגיאה: מספר הדרכון כבר קיים במערכת. לא ניתן להירשם פעמיים."
        cur.fetchall()

        try:
            cur.execute(
                "INSERT INTO customer (email, first_name, last_name) VALUES (?, ?, ?)",
                (email, data['first_name'], data['last_name'])
            )

            cur.execute(
                """INSERT INTO registered_customer 
                   (email, password, passport_number, date_of_birth, registration_date) 
                   VALUES (?, ?, ?, ?, ?)""",
                (email, data['password'], passport, data['birth_date'], date.today())
            )

            cur.execute(
                "INSERT INTO customer_phone_number (email, phone_number) VALUES (?, ?)",
                (email, data['phone_main'])
            )

            if 'extra_phones' in data:
                for phone in data['extra_phones']:
                    if phone.strip():
                        cur.execute(
                            "INSERT INTO customer_phone_number (email, phone_number) VALUES (?, ?)",
                            (email, phone)
                        )

            return True, "נרשמת בהצלחה! כעת ניתן להתחבר"

        except Exception as e:
            print(f"Database error during signup: {e}")
            return False, "אירעה שגיאה בתהליך הרישום. ייתכן שאחד הפרטים אינו תקין."


def get_flight_with_aircraft(flight_number: int):
    sql = """
    SELECT f.flight_number, f.departure_datetime, f.origin_airport, f.destination_airport,
           f.aircraft_id_number, f.status
    FROM flight f
    WHERE f.flight_number = ?;
    """
    with db_conn() as cur:
        cur.execute(sql, (flight_number,))
        return cur.fetchone()


def get_classes_for_aircraft(aircraft_id_number: int):
    sql = """
    SELECT type, number_of_rows, number_of_columns
FROM class
WHERE aircraft_id_number = ?
ORDER BY CASE type
    WHEN 'BUSINESS' THEN 1
    WHEN 'ECONOMY' THEN 2
    ELSE 3
END;
    """
    with db_conn() as cur:
        cur.execute(sql, (aircraft_id_number,))
        return cur.fetchall()


def get_seats_for_flight_class(flight_number: int, class_type: str):
    sql = """
    SELECT `aircraft_id_number`, `class_type`, `row_number`, `column_number`, `price`
    FROM `seats_in_flights`
    WHERE `flight_number` = ?
      AND `class_type` = ?
    ORDER BY `row_number`, `column_number`;
    """
    with db_conn() as cur:
        cur.execute(sql, (flight_number, class_type))
        return cur.fetchall()


def get_taken_seats_for_flight(flight_number: int):

    sql = """
    SELECT sir.aircraft_id_number, sir.class_type, sir.row_number, sir.column_number
    FROM seats_in_reservation sir
    JOIN reservations r ON r.reservation_code = sir.reservation_code
    WHERE r.flight_number = ?
      AND r.reservations_status = 'ACTIVE';
    """
    with db_conn() as cur:
        cur.execute(sql, (flight_number,))
        rows = cur.fetchall()
        return set((x["aircraft_id_number"], x["class_type"], x["row_number"], x["column_number"]) for x in rows)


def create_reservation_with_seats(email: str, flight_number: int, seats: list[dict]) -> int:
    with db_tx() as (conn, cur):
        cur.execute("SELECT aircraft_id_number FROM flight WHERE flight_number=?", (flight_number,))
        f = cur.fetchone()
        cur.fetchall()

        if not f:
            raise ValueError("טיסה לא קיימת")
        aircraft_id = f["aircraft_id_number"]

        total = 0.0
        for s in seats:
            cur.execute("""
                SELECT price
                FROM seats_in_flights
                WHERE aircraft_id_number=? AND flight_number=? AND class_type=? AND `row_number`=? AND column_number=?
            """, (aircraft_id, flight_number, s["class_type"], s["row_number"], s["column_number"]))

            seat_row = cur.fetchone()
            cur.fetchall()

            if not seat_row:
                raise ValueError(f"מושב {s['row_number']}-{s['column_number']} לא נמצא בטיסה זו")

            total += float(seat_row["price"] or 0)

        while True:
            reservation_code = random.randint(8000, 9999)
            cur.execute("SELECT 1 FROM reservations WHERE reservation_code=?", (reservation_code,))
            res_exists = cur.fetchone()
            cur.fetchall()
            if not res_exists:
                break

        cur.execute("SELECT 1 FROM customer WHERE email=?", (email,))
        cust_exists = cur.fetchone()
        cur.fetchall()

        if not cust_exists:
            cur.execute("INSERT INTO customer(email, first_name, last_name) VALUES (?, NULL, NULL)", (email,))

        cur.execute("""
            INSERT INTO reservations
            (reservation_code, reservations_status, reservation_date, total_payment, email, flight_number)
            VALUES (?, 'ACTIVE', DATE('now'), ?, ?, ?);
        """, (reservation_code, total, email, flight_number))

        for s in seats:
            cur.execute("""
                INSERT INTO seats_in_reservation
                (reservation_code, aircraft_id_number, class_type, `row_number`, column_number)
                VALUES (?, ?, ?, ?, ?)
            """, (reservation_code, aircraft_id, s["class_type"], s["row_number"], s["column_number"]))

        return reservation_code

def get_airport_countries():
    sql = """
        SELECT DISTINCT country
        FROM airport
        WHERE country IS NOT NULL AND country <> ''
        ORDER BY country;
    """
    with db_conn() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return [r["country"] for r in rows]

def authenticate_manager(manager_id: int, password: str):
    sql = """
        SELECT id_number, first_name, last_name
        FROM manager
        WHERE id_number = ? AND password = ?
        LIMIT 1;
    """
    with db_conn() as cur:
        cur.execute(sql, (manager_id, password))
        return cur.fetchone()

def get_all_flights_with_hours_and_occupancy():
    sql = """
    SELECT
  f.flight_number,
  f.aircraft_id_number,
  f.origin_airport,
  f.destination_airport,
  f.departure_datetime,
  f.status,

  -- REPLACEMENT 1: SQLite replacement for TIMESTAMPDIFF(HOUR, ...)
  -- Calculates difference in days, multiplies by 24 for hours, and casts to int
  CAST((julianday(f.departure_datetime) - julianday('now')) * 24 AS INTEGER) AS hours_to_departure,

  -- REPLACEMENT 2: SQLite boolean logic
  -- Returns 1 (True) or 0 (False)
  (f.departure_datetime < datetime('now')) AS is_past,

  COALESCE(st.total_seats, 0) AS total_seats,
  COALESCE(tk.taken_seats, 0) AS taken_seats,

  CASE
    WHEN COALESCE(st.total_seats, 0) > 0
     AND COALESCE(st.total_seats, 0) = COALESCE(tk.taken_seats, 0)
    THEN 1 ELSE 0
  END AS is_full

FROM flight f
LEFT JOIN (
    SELECT flight_number, COUNT(*) AS total_seats
    FROM seats_in_flights
    GROUP BY flight_number
) st ON st.flight_number = f.flight_number

LEFT JOIN (
    SELECT r.flight_number, COUNT(*) AS taken_seats
    FROM reservations r
    JOIN seats_in_reservation sir ON sir.reservation_code = r.reservation_code
    WHERE r.reservations_status = 'ACTIVE'
    GROUP BY r.flight_number
) tk ON tk.flight_number = f.flight_number

ORDER BY f.departure_datetime;
    """
    with db_conn() as cur:
        cur.execute(sql)
        rows = cur.fetchall() or []

    rows_list = []
    for r in rows:
        mutable_r = dict(r)
        mutable_r["is_past"] = bool(r["is_past"])
        mutable_r["is_full"] = bool(r["is_full"])
        rows_list.append(mutable_r)
    return rows_list

def get_all_airports():
    sql = "SELECT airport_name FROM airport ORDER BY airport_name;"
    with db_conn() as cur:
        cur.execute(sql)
        return [r["airport_name"] for r in cur.fetchall()]
def aircraft_id_exists(aircraft_id_number: int) -> bool:
    sql = "SELECT 1 FROM aircraft WHERE aircraft_id_number = ? LIMIT 1;"
    with db_conn() as cur:
        cur.execute(sql, (aircraft_id_number,))
        return cur.fetchone() is not None


def generate_unique_aircraft_id_4_digits(max_tries: int = 5000) -> int:
    for _ in range(max_tries):
        candidate = random.randint(1000, 9999)
        if not aircraft_id_exists(candidate):
            return candidate
    raise RuntimeError("לא הצלחתי לייצר מספר מטוס ייחודי (4 ספרות).")


def create_aircraft(size: str, manufacturer: str, purchase_date):
    sql = """
    INSERT INTO aircraft (aircraft_id_number, size, manufacturer, purchase_date)
    VALUES (?, ?, ?, ?);
    """
    new_id = generate_unique_aircraft_id_4_digits()
    with db_conn() as cur:
        cur.execute(sql, (new_id, size, manufacturer, purchase_date))
    return new_id

def create_reservation_with_seats_with_customer_details(
    email: str,
    first_name: str,
    last_name: str,
    phones: list[str],
    flight_number: int,
    seats: list[dict]
) -> int:
    email = (email or "").strip().lower()
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    phones = [str(p).strip() for p in (phones or []) if str(p).strip()]

    if not email or not first_name or not last_name or not phones:
        raise ValueError("חסרים פרטי לקוח (אימייל/שם/טלפון).")

    with db_tx() as (conn, cur):
        cur.execute("SELECT 1 FROM customer WHERE email=?", (email,))
        exists = cur.fetchone()
        cur.fetchall()

        if not exists:
            cur.execute(
                "INSERT INTO customer (email, first_name, last_name) VALUES (?, ?, ?)",
                (email, first_name, last_name)
            )
        else:
            cur.execute(
                "UPDATE customer SET first_name=?, last_name=? WHERE email=?",
                (first_name, last_name, email)
            )

        cur.execute("DELETE FROM customer_phone_number WHERE email=?", (email,))
        for p in phones:
            cur.execute(
                "INSERT INTO customer_phone_number (email, phone_number) VALUES (?, ?)",
                (email, p)
            )

        cur.execute("SELECT aircraft_id_number FROM flight WHERE flight_number=?", (flight_number,))
        f = cur.fetchone()
        cur.fetchall()

        if not f:
            raise ValueError("טיסה לא קיימת")
        aircraft_id = f["aircraft_id_number"]

        total = 0.0
        for s in seats:
            cur.execute("""
                SELECT price
                FROM seats_in_flights
                WHERE aircraft_id_number=? AND flight_number=? AND class_type=? AND `row_number`=? AND column_number=?
            """, (aircraft_id, flight_number, s["class_type"], s["row_number"], s["column_number"]))
            seat_row = cur.fetchone()
            cur.fetchall()

            if not seat_row:
                raise ValueError(f"מושב {s['row_number']}-{s['column_number']} לא נמצא בטיסה זו")

            total += float(seat_row["price"] or 0)

        while True:
            reservation_code = random.randint(8000, 9999)
            cur.execute("SELECT 1 FROM reservations WHERE reservation_code=?", (reservation_code,))
            res_exists = cur.fetchone()
            cur.fetchall()
            if not res_exists:
                break

        cur.execute("""
            INSERT INTO reservations
            (reservation_code, reservations_status, reservation_date, total_payment, email, flight_number)
            VALUES (?, 'ACTIVE', CURRENT_DATE, ?, ?, ?);
        """, (reservation_code, total, email, flight_number))

        for s in seats:
            cur.execute("""
                INSERT INTO seats_in_reservation
                (reservation_code, aircraft_id_number, class_type, `row_number`, column_number)
                VALUES (?, ?, ?, ?, ?)
            """, (reservation_code, aircraft_id, s["class_type"], s["row_number"], s["column_number"]))

        return reservation_code


def crew_member_exists_in_any_table(id_number: int) -> bool:
    """
    בודק אם ת"ז כבר קיימת כאיש צוות או כמנהל
    (pilot / flight_attendant / manager)
    """
    sql = """
    SELECT 1 FROM pilot WHERE id_number = ?
    UNION
    SELECT 1 FROM flight_attendant WHERE id_number = ?
    UNION
    SELECT 1 FROM manager WHERE id_number = ?
    LIMIT 1;
    """
    with db_conn() as cur:
        cur.execute(sql, (id_number, id_number, id_number))
        return cur.fetchone() is not None


def create_pilot(
    id_number: int,
    first_name: str,
    last_name: str,
    city: str,
    street: str,
    house_number: int,
    phone_number: int,
    employment_start_date,
    long_flight_certification: int
):
    sql = """
    INSERT INTO pilot
      (id_number, first_name, last_name, city, street, house_number, phone_number, employment_start_date, long_flight_certification)
    VALUES
      (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    with db_conn() as cur:
        cur.execute(sql, (
            id_number, first_name, last_name, city, street,
            house_number, phone_number, employment_start_date, long_flight_certification
        ))


def create_attendant(
    id_number: int,
    first_name: str,
    last_name: str,
    city: str,
    street: str,
    house_number: int,
    phone_number: int,
    employment_start_date,
    long_flight_certification: int
):
    sql = """
    INSERT INTO flight_attendant
      (id_number, first_name, last_name, city, street, house_number, phone_number, employment_start_date, long_flight_certification)
    VALUES
      (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    with db_conn() as cur:
        cur.execute(sql, (
            id_number, first_name, last_name, city, street,
            house_number, phone_number, employment_start_date, long_flight_certification
        ))


def create_aircraft_with_classes_and_seats(
    *,
    size: str,
    manufacturer: str,
    purchase_date,
    econ_rows: int,
    econ_cols: int,
    bus_rows=None,
    bus_cols=None
):
    new_id = generate_unique_aircraft_id_4_digits()

    sql_air = """
    INSERT INTO `aircraft` (`aircraft_id_number`, `size`, `manufacturer`, `purchase_date`)
    VALUES (?, ?, ?, ?);
    """

    sql_class = """
    INSERT INTO `class` (`aircraft_id_number`, `type`, `number_of_rows`, `number_of_columns`)
    VALUES (?, ?, ?, ?);
    """

    sql_seat = """
    INSERT INTO `seat` (`aircraft_id_number`, `class_type`, `row_number`, `column_number`)
    VALUES (?, ?, ?, ?);
    """

    def build_seats(aircraft_id: int, class_type: str, rows: int, cols: int):
        return [(aircraft_id, class_type, r, c)
                for r in range(1, rows + 1)
                for c in range(1, cols + 1)]

    with db_conn() as cur:
        cur.execute(sql_air, (new_id, size, manufacturer, purchase_date))

        cur.execute(sql_class, (new_id, "ECONOMY", econ_rows, econ_cols))

        if size == "LARGE":
            if bus_rows is None or bus_cols is None:
                raise ValueError("חובה להזין נתוני BUSINESS למטוס גדול.")
            cur.execute(sql_class, (new_id, "BUSINESS", int(bus_rows), int(bus_cols)))

        econ_seats = build_seats(new_id, "ECONOMY", int(econ_rows), int(econ_cols))
        cur.executemany(sql_seat, econ_seats)

        if size == "LARGE":
            bus_seats = build_seats(new_id, "BUSINESS", int(bus_rows), int(bus_cols))
            cur.executemany(sql_seat, bus_seats)

    return new_id
