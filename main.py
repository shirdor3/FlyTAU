from flask import Flask, render_template, request, jsonify, session, url_for, redirect
from flask_session import Session
import json
from datetime import datetime,timedelta
from utils import (db_conn, get_active_reservations_for_guest, cancel_reservation_for_guest,
                   get_all_flights_with_hours, cancel_flight_and_linked_reservations, get_flight_duration_minutes, is_long_flight,
    get_available_aircraft, get_available_pilots, get_available_attendants,
    required_crew_counts, create_flight_with_crew_and_prices, generate_unique_flight_number, authenticate_user, signup_user, get_airport_countries, authenticate_manager, get_flight_with_aircraft,
    get_classes_for_aircraft, is_card_exp_valid,
    get_seats_for_flight_class,
    get_taken_seats_for_flight,
    create_reservation_with_seats, get_all_flights_with_hours_and_occupancy, get_all_airports, get_seats_for_aircraft_class, create_reservation_with_seats_with_customer_details, create_pilot, crew_member_exists_in_any_table,create_attendant,create_aircraft_with_classes_and_seats)

from utils_reports import (
    report_avg_occupancy,
    report_revenue_by_combo,
    report_staff_hours,
    report_cancellation_rate,
    report_aircraft_monthly_summary)

app = Flask(__name__)
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR="flask_session_data",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
    SESSION_REFRESH_EACH_REQUEST=True,
    SESSION_COOKIE_SECURE=False
)
Session(app)


@app.route('/')
def homepage(): #Render the homepage template
    return render_template('homepage.html')

@app.route('/login', methods=['GET', 'POST'])
def login(): #Customer login validate input authenticate set session and redirect
    if request.method == "POST":
        email = (request.form.get("email")).strip().lower()
        password = (request.form.get("password")).strip()
        if not email or not password:
            return render_template('login.html')
        user = authenticate_user(email, password)
        if user:
            session['user_email'] = user['email']
            session['user_name'] = user['first_name']
            return redirect ('/flight_search_customers')
        else:
            return render_template('login.html', message="Invalid Details")
    else:
        return render_template('login.html')


@app.route('/history', methods=['GET'])
def history(): #Show the logged in customer's reservation history with optional status filtering
    if not session.get('user_email'):
        return redirect(url_for('login'))
    user_email = session['user_email']
    status_filter = request.args.get('status', 'all')
    query = """
        SELECT 
            r.reservation_code, 
            r.flight_number, 
            r.total_payment,
            f.departure_datetime, 
            f.origin_airport, 
            f.destination_airport,
            r.reservations_status as raw_status,
            CASE 
                WHEN r.reservations_status = 'ACTIVE' AND f.departure_datetime >= datetime('now') THEN 'פעילה'
                WHEN r.reservations_status = 'ACTIVE' AND f.departure_datetime < datetime('now') THEN 'בוצעה'
                WHEN r.reservations_status = 'CUSTOMER_CANCELED' THEN 'ביטול לקוח'
                WHEN r.reservations_status = 'SYSTEM_CANCELED' THEN 'ביטול מערכת'
                ELSE r.reservations_status
            END as display_status
        FROM reservations r
        JOIN flight f ON r.flight_number = f.flight_number
        WHERE r.email = ?
    """
    params = [user_email]
    if status_filter == 'active_future':
        query += " AND r.reservations_status = 'ACTIVE' AND f.departure_datetime >= datetime('now')"
    elif status_filter == 'completed':
        query += " AND r.reservations_status = 'ACTIVE' AND f.departure_datetime < datetime('now')"
    elif status_filter == 'customer_cancelled':
        query += " AND r.reservations_status = 'CUSTOMER_CANCELED'"
    elif status_filter == 'system_cancelled':
        query += " AND r.reservations_status = 'SYSTEM_CANCELED'"

    query += " ORDER BY f.departure_datetime DESC"

    with db_conn() as cur:
        cur.execute(query, params)
        orders = cur.fetchall()
    now = datetime.now()
    orders_list = []
    for o in orders:
        o = dict(o)
        if o['departure_datetime']:
            departure_datetime = datetime.strptime(o['departure_datetime'], '%Y-%m-%d %H:%M:%S')
            o['departure_datetime'] = departure_datetime
            time_diff = departure_datetime - now
            o['is_urgent'] = time_diff < timedelta(hours=36) and time_diff > timedelta(0)
        else:
            o['is_urgent'] = False

        payment_value = o.get('total_payment') or o.get('total_price') or 0
        o['cancellation_fee'] = round(float(payment_value) * 0.05, 2)
        orders_list.append(o)

    return render_template('history.html', orders=orders_list, current_filter=status_filter)

@app.route('/cancel_reservation', methods=['POST'])
def cancel_reservation(): #Cancel a logged in customer's reservation and update payment based on time of cancellation
    if not session.get('user_email'):
        return redirect(url_for('login'))

    res_code = request.form.get('reservation_code')
    user_email = session['user_email']

    if res_code:
        with db_conn() as cur:
            cur.execute("""
                SELECT f.departure_datetime, r.total_payment 
                FROM reservations r
                JOIN flight f ON r.flight_number = f.flight_number
                WHERE r.reservation_code = ? AND r.email = ?
            """, (res_code, user_email))

            result = cur.fetchone()

            if result:
                original_price = result['total_payment']
                now = datetime.now()
                cur.execute("DELETE FROM seats_in_reservation WHERE reservation_code = ?", (res_code,))
                flight_time = datetime.strptime(result['departure_datetime'], '%Y-%m-%d %H:%M:%S')
                if flight_time > now + timedelta(hours=36):
                    new_price = float(original_price) * 0.05
                    cur.execute("""
                        UPDATE reservations 
                        SET reservations_status = 'CUSTOMER_CANCELED', 
                            total_payment = ?
                        WHERE reservation_code = ?
                    """, (new_price, res_code))
                else:
                    cur.execute("""
                        UPDATE reservations 
                        SET reservations_status = 'CUSTOMER_CANCELED'
                        WHERE reservation_code = ?
                    """, (res_code,))
    return redirect(url_for('history'))

@app.route('/flight_search_customers', methods=["GET"])
def flight_search_customers(): #Search upcoming active flights for logged in customers optional filters by date/countries
    departure_date = (request.args.get("departure_datetime") or "").strip()
    origin_country = (request.args.get("origin_country") or "").strip()
    destination_country = (request.args.get("destination_country") or "").strip()

    query = """
        SELECT 
            f.flight_number, 
            f.departure_datetime, 
            f.origin_airport, 
            a1.country AS origin_country,
            f.destination_airport, 
            a2.country AS destination_country
        FROM flight f
        JOIN airport a1 ON f.origin_airport = a1.airport_name
        JOIN airport a2 ON f.destination_airport = a2.airport_name
        WHERE f.departure_datetime >= datetime('now') AND f.status = 'ACTIVE'

    """
    params = []

    if departure_date:
        query += " AND DATE(f.departure_datetime) = ?"
        params.append(departure_date)

    if origin_country:
        query += " AND a1.country LIKE ?"
        params.append(f"%{origin_country}%")

    if destination_country:
        query += " AND a2.country LIKE ?"
        params.append(f"%{destination_country}%")

    query += " ORDER BY f.departure_datetime"

    with db_conn() as cursor:
        cursor.execute(query, params)
        flights = cursor.fetchall()

    return render_template('flight_search_customers.html', flights=flights)


@app.route('/signup', methods=['GET', 'POST'])
def signup(): #Register a new customer account and start a logged in session
    if request.method == 'POST':
        user_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email').strip().lower(),
            'phone_main': request.form.get('phone_main'),
            'extra_phones': request.form.getlist('extra_phones[]'),
            'passport': request.form.get('passport'),
            'birth_date': request.form.get('birth_date'),
            'password': request.form.get('password')
        }

        success, message = signup_user(user_data)

        if success:
            session['user_email'] = user_data['email']
            session['user_name'] = user_data['first_name']
            session['user_last_name'] = user_data['last_name']
            return redirect('/flight_search_customers')
        else:
            return render_template('signup.html', message=message)
    return render_template('signup.html')

@app.route('/flight_search_guest', methods=["GET"])
def flight_search_guest(): #Search upcoming active flights for guests and show available countries for filtering
    departure_date = (request.args.get("departure_datetime") or "").strip()
    origin_country = (request.args.get("origin_country") or "").strip()
    destination_country = (request.args.get("destination_country") or "").strip()
    searched = any([departure_date, origin_country, destination_country])
    query = """
        SELECT 
            f.flight_number, 
            f.departure_datetime, 
            f.origin_airport, 
            a1.country AS origin_country,
            f.destination_airport, 
            a2.country AS destination_country
        FROM flight f
        JOIN airport a1 ON f.origin_airport = a1.airport_name
        JOIN airport a2 ON f.destination_airport = a2.airport_name
        WHERE f.departure_datetime >= datetime('now') AND f.status = 'ACTIVE'

    """
    params = []
    if departure_date:
        query += " AND DATE(f.departure_datetime) = ?"
        params.append(departure_date)
    if origin_country:
        query += " AND a1.country LIKE ?"
        params.append(f"%{origin_country}%")
    if destination_country:
        query += " AND a2.country LIKE ?"
        params.append(f"%{destination_country}%")
    query += " ORDER BY f.departure_datetime"
    with db_conn() as cursor:
        cursor.execute(query, params)
        flights = cursor.fetchall()

    countries = get_airport_countries()
    return render_template('flight_search_guest.html',
                           flights=flights,
                           searched=searched,
                           countries=countries)

@app.route('/results', methods=["GET"])
def results(): #Show flight search results by date and/or origin/destination airport
    departure_date = (request.args.get("departure_datetime") or "").strip()
    origin_airport = (request.args.get("origin_airport") or "").strip().upper()
    destination_airport = (request.args.get("destination_airport") or "").strip().upper()
    query = """
        SELECT flight_number, departure_datetime, origin_airport, destination_airport
        FROM flight
        WHERE departure_datetime >= CURRENT_DATE AND status = 'ACTIVE'
    """
    params = []
    if departure_date:
        query += " AND DATE(departure_datetime) = ?"
        params.append(departure_date)
    if origin_airport:
        query += " AND origin_airport = ?"
        params.append(origin_airport)
    if destination_airport:
        query += " AND destination_airport = ?"
        params.append(destination_airport)
    query += " ORDER BY departure_datetime"
    with db_conn() as cursor:
        cursor.execute(query, params)
        flights = cursor.fetchall()
    return render_template(
        "results.html",
        flights=flights,
        departure_date=departure_date,
        origin_airport=origin_airport,
        destination_airport=destination_airport
    )

@app.route('/login_managers', methods=['GET', 'POST'])
def login_managers(): #Handle manager login validate ID and password set session and redirect
    if request.method == "POST":
        tz_raw = (request.form.get("tz") or "").strip()
        password = (request.form.get("password") or "").strip()
        try:
            tz = int(tz_raw)
        except ValueError:
            return render_template("login_managers.html", message="תעודת זהות לא תקינה")
        if not password:
            return render_template("login_managers.html", message="חובה להזין סיסמה")
        manager = authenticate_manager(tz, password)
        if manager:
            session['manager_id'] = manager['id_number']
            session['manager_name'] = manager['first_name']
            return redirect('/cancel_flight_manager')
        else:
            return render_template("login_managers.html", message="Invalid Details")
    return render_template('login_managers.html')

@app.route("/add_crew", methods=["GET", "POST"])
def add_crew(): #Add a new crew member pilot/attendant with validation and duplicate ID prevention
    if request.method == "GET":
        return render_template("add_crew.html")
    role = (request.form.get("role") or "").strip().lower()
    tz_raw = (request.form.get("tz") or "").strip()
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    phone_raw = (request.form.get("phone") or "").strip()
    city = (request.form.get("city") or "").strip()
    street = (request.form.get("street") or "").strip()
    house_raw = (request.form.get("house_number") or "").strip()
    long_cert = 1 if request.form.get("long_flight_certification") == "1" else 0
    try:
        if role not in ("pilot", "attendant"):
            raise ValueError("חובה לבחור תפקיד (טייס/דייל).")
        if not tz_raw.isdigit():
            raise ValueError("תעודת זהות חייבת להכיל ספרות בלבד.")
        tz = int(tz_raw)
        if not phone_raw.isdigit():
            raise ValueError("טלפון חייב להכיל ספרות בלבד.")
        phone_number = int(phone_raw)
        house_number = int(house_raw)
        employment_start_date = datetime.today()
        if crew_member_exists_in_any_table(tz):
            raise ValueError("כבר קיים עובד עם תעודת זהות זו במערכת.")
    except Exception as e:
        return render_template("add_crew.html", error=f"שגיאה בהוספת איש צוות: {e}")

    try:
        if role == "pilot":
            create_pilot(
                id_number=tz,
                first_name=first_name,
                last_name=last_name,
                city=city,
                street=street,
                house_number=house_number,
                phone_number=phone_number,
                employment_start_date=employment_start_date,
                long_flight_certification=long_cert
            )
        else:
            create_attendant(
                id_number=tz,
                first_name=first_name,
                last_name=last_name,
                city=city,
                street=street,
                house_number=house_number,
                phone_number=phone_number,
                employment_start_date=employment_start_date,
                long_flight_certification=long_cert
            )
        return render_template("add_crew.html", message="איש צוות נוסף בהצלחה ✅")

    except Exception as e:
        return render_template("add_crew.html", error=f"שגיאה בהוספת איש צוות: {e}")

@app.route("/manager_buy_aircraft", methods=["GET", "POST"])
def manager_buy_aircraft(): #Manager buy a new aircraft choose manufacturer and size then create seat layout
    manufacturers = ["BOEING", "AIRBUS", "DASSAULT"]
    sizes = ["SMALL", "LARGE"]

    if request.method == "GET":
        return render_template(
            "manager_buy_aircraft.html",
            manufacturers=manufacturers,
            sizes=sizes,
            step=1,
            selected_manufacturer="",
            selected_size=""
        )

    step = (request.form.get("step") or "1").strip()

    manufacturer = (request.form.get("manufacturer") or "").strip().upper()
    size = (request.form.get("size") or "").strip().upper()

    if manufacturer not in manufacturers:
        return render_template(
            "manager_buy_aircraft.html",
            manufacturers=manufacturers,
            sizes=sizes,
            step=1,
            selected_manufacturer="",
            selected_size="",
            error="יצרן לא תקין."
        )

    if size not in sizes:
        return render_template(
            "manager_buy_aircraft.html",
            manufacturers=manufacturers,
            sizes=sizes,
            step=1,
            selected_manufacturer=manufacturer,
            selected_size="",
            error="גודל לא תקין."
        )

    if step == "1":
        return render_template(
            "manager_buy_aircraft.html",
            manufacturers=manufacturers,
            sizes=sizes,
            step=2,
            selected_manufacturer=manufacturer,
            selected_size=size
        )

    purchase_date = datetime.today().date()

    try:
        econ_rows = int(request.form.get("econ_rows"))
        econ_cols = int(request.form.get("econ_cols"))
        if econ_rows < 1 or econ_cols < 1:
            raise ValueError("ערכי ECONOMY חייבים להיות חיוביים.")

        bus_rows = None
        bus_cols = None
        if size == "LARGE":
            bus_rows = int(request.form.get("bus_rows"))
            bus_cols = int(request.form.get("bus_cols"))
            if bus_rows < 1 or bus_cols < 1:
                raise ValueError("ערכי BUSINESS חייבים להיות חיוביים.")

    except Exception as e:
        return render_template(
            "manager_buy_aircraft.html",
            manufacturers=manufacturers,
            sizes=sizes,
            step=2,
            selected_manufacturer=manufacturer,
            selected_size=size,
            error=f"נתוני מחלקות לא תקינים: {e}"
        )

    try:
        new_aircraft_id = create_aircraft_with_classes_and_seats(
            size=size,
            manufacturer=manufacturer,
            purchase_date=purchase_date,
            econ_rows=econ_rows,
            econ_cols=econ_cols,
            bus_rows=bus_rows,
            bus_cols=bus_cols
        )

    except Exception as e:
        return render_template(
            "manager_buy_aircraft.html",
            manufacturers=manufacturers,
            sizes=sizes,
            step=2,
            selected_manufacturer=manufacturer,
            selected_size=size,
            error=f"שגיאה בהוספת מטוס: {e}"
        )

    return render_template(
        "manager_buy_aircraft.html",
        manufacturers=manufacturers,
        sizes=sizes,
        step=1,
        selected_manufacturer="",
        selected_size="",
        message=f"המטוס נרכש ונוסף בהצלחה! מספר מטוס: {new_aircraft_id}"
    )

@app.route("/sign_in_show_tickets", methods=["GET", "POST"])
def sign_in_show_tickets(): #Let a guest enter email and reservation code and view active reservations
    if request.method == "GET":
        return render_template("sign_in_show_tickets.html")

    email = (request.form.get("email") or "").strip().lower()
    reservation_code_raw = request.form.get("reservation_code")

    try:
        reservation_code = int(reservation_code_raw)
    except:
        return render_template("sign_in_show_tickets.html", error="קוד לא תקין")

    reservations = get_active_reservations_for_guest(email, reservation_code)
    now = datetime.now()
    reservations_list = []
    for r in reservations:
        r = dict(r)
        if r['departure_datetime']:
            datetime_object = datetime.strptime(r['departure_datetime'], '%Y-%m-%d %H:%M:%S')
            time_diff = datetime_object - now
            r['is_urgent'] = time_diff < timedelta(hours=36) and time_diff > timedelta(0)
        else:
            r['is_urgent'] = False
        payment_value = r.get('total_payment') or 0
        r['cancellation_fee'] = round(float(payment_value) * 0.05, 2)
        reservations_list.append(r)
    return render_template("tickets_results.html", reservations=reservations_list, email=email)


@app.route("/cancel_reservation_post", methods=["POST"])
def cancel_reservation_post(): #Cancel a guest reservation using email and reservation code and show updated results
    email = (request.form.get("email") or "").strip().lower()
    reservation_code_raw = request.form.get("reservation_code")
    try:
        reservation_code = int(reservation_code_raw)
        if reservation_code <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return render_template("tickets_results.html",
                               reservations=[],
                               email=email,
                               error="קוד הזמנה לא תקין (חייב להיות מספר שלם וחיובי).")

    if not email:
        return render_template("tickets_results.html",
                               reservations=[],
                               email=email,
                               error="אימייל לא תקין.")

    ok = cancel_reservation_for_guest(email, reservation_code)
    reservations = get_active_reservations_for_guest(email, reservation_code)

    if not ok:
        return render_template("tickets_results.html",
                               reservations=reservations,
                               email=email,
                               error="לא ניתן לבטל: ההזמנה לא פעילה / לא קיימת / לא שייכת לאימייל.")

    return render_template("tickets_results.html",
                           reservations=reservations,
                           email=email,
                           message="ההזמנה בוטלה בהצלחה.")


@app.route("/cancel_flight_manager", methods=["GET"])
def update_flight_manager(): #Show manager flight list with filters: upcoming, full, past, canceled
    flt = (request.args.get("filter") or "all").strip().lower()

    flights = get_all_flights_with_hours_and_occupancy()

    if flt == "active_upcoming":
        flights = [f for f in flights if f["status"] == "ACTIVE" and not f["is_past"]]
    elif flt == "full":
        flights = [f for f in flights if f["status"] == "ACTIVE" and not f["is_past"] and f["is_full"]]
    elif flt == "past":
        flights = [f for f in flights if f["status"] == "ACTIVE" and f["is_past"]]
    elif flt == "canceled":
        flights = [f for f in flights if f["status"] == "CANCELED"]

    return render_template("cancel_flight_manager.html", flights=flights, selected_filter=flt)

@app.route("/cancel_flight_post", methods=["POST"])
def cancel_flight_post(): #Cancel a flight and update linked reservations
    flight_number_raw = request.form.get("flight_number")

    try:
        flight_number = int(flight_number_raw)
        if flight_number <= 0:
            raise ValueError
    except (TypeError, ValueError):
        flights = get_all_flights_with_hours()
        return render_template("cancel_flight_manager.html", flights=flights, error="מספר טיסה לא תקין.")

    result = cancel_flight_and_linked_reservations(flight_number)
    flights = get_all_flights_with_hours()

    if not result["ok"]:
        if result["reason"] == "NOT_FOUND":
            return render_template("cancel_flight_manager.html", flights=flights, error="הטיסה לא נמצאה.")
        if result["reason"] == "ALREADY_CANCELED":
            return render_template("cancel_flight_manager.html", flights=flights, error="הטיסה כבר בוטלה.")
        if result["reason"] == "TOO_SOON":
            return render_template("cancel_flight_manager.html", flights=flights, error="לא ניתן לבטל טיסה בתוך 72 שעות מההמראה.")
        return render_template("cancel_flight_manager.html", flights=flights, error="לא ניתן לבטל את הטיסה.")

    msg = f"הטיסה {flight_number} בוטלה. עודכנו {result['reservations_updated']} הזמנות פעילות ל-SYSTEM_CANCELED ואופס התשלום."
    return render_template("cancel_flight_manager.html", flights=flights, message=msg)

@app.route("/manager_add_flight", methods=["GET", "POST"])
def manager_add_flight(): #Create a new flight with aircraft crew and prices
    airports = get_all_airports()
    if request.method == "GET":
        return render_template("manager_add_flight.html", airports=airports)

    def render_step2( #Helper render step 2 of the add flight flow with all needed data and messages
        *,
        origin: str,
        destination: str,
        aircraft_size_selected: str,
        dep_date: str,
        dep_time: str,
        duration: int,
        arrival_dt,
        long_required: bool,
        aircraft_list,
        pilots_list,
        attendants_list,
        generated_flight_number: int,
        error: str | None = None,
        message: str | None = None
    ):
        req = required_crew_counts(aircraft_size_selected)

        return render_template(
            "manager_add_flight_step2.html",
            origin=origin,
            destination=destination,
            aircraft_size_selected=aircraft_size_selected,
            dep_date=dep_date,
            dep_time=dep_time,
            duration=duration,
            arrival_dt=arrival_dt,
            long_required=long_required,
            aircraft_list=aircraft_list,
            pilots_list=pilots_list,
            attendants_list=attendants_list,
            generated_flight_number=generated_flight_number,
            req=req,
            error=error,
            message=message
        )

    if request.form.get("aircraft_id_number"):
        origin = (request.form.get("origin_airport") or "").strip().upper()
        destination = (request.form.get("destination_airport") or "").strip().upper()
        dep_date = (request.form.get("departure_date") or "").strip()
        dep_time = (request.form.get("departure_time") or "").strip()

        selected_size = (request.form.get("aircraft_size") or "").strip().upper()

        flight_number_raw = request.form.get("flight_number")
        aircraft_id_raw = request.form.get("aircraft_id_number")

        pilots_ids_raw = request.form.getlist("pilots_ids")
        attendants_ids_raw = request.form.getlist("attendants_ids")

        price_econ_raw = request.form.get("price_ECONOMY")
        price_bus_raw = request.form.get("price_BUSINESS")
        duration = get_flight_duration_minutes(origin, destination)
        if duration is None:
            return render_template(
                "manager_add_flight.html",
                airports=airports,
                error="המסלול שנבחר לא קיים במערכת."
            )

        long_required = is_long_flight(int(duration))

        try:
            departure_dt = datetime.strptime(f"{dep_date} {dep_time}", "%Y-%m-%d %H:%M")
        except Exception:
            return render_template(
                "manager_add_flight.html",
                airports=airports,
                error="תאריך/שעה לא תקינים."
            )

        arrival_dt = departure_dt + timedelta(minutes=int(duration))
        aircraft_list = get_available_aircraft(departure_dt, arrival_dt, origin, long_required)
        aircraft_list = [a for a in (aircraft_list or []) if (a["size"] or "").upper() == selected_size]

        pilots_list = get_available_pilots(departure_dt, arrival_dt, origin, long_required)
        attendants_list = get_available_attendants(departure_dt, arrival_dt, origin, long_required)

        try:
            generated_flight_number = int(flight_number_raw)
        except Exception:
            generated_flight_number = generate_unique_flight_number()

        try:
            flight_number = int(flight_number_raw)
            aircraft_id_number = int(aircraft_id_raw)

            pilots_ids = [int(x) for x in pilots_ids_raw]
            attendants_ids = [int(x) for x in attendants_ids_raw]

            if len(set(pilots_ids)) != len(pilots_ids):
                raise ValueError("נבחר אותו טייס יותר מפעם אחת.")
            if len(set(attendants_ids)) != len(attendants_ids):
                raise ValueError("נבחר אותו דייל יותר מפעם אחת.")

            if price_econ_raw is None or price_econ_raw == "":
                raise ValueError("Missing ECONOMY price")
            price_econ = float(price_econ_raw)
            if price_econ < 0:
                raise ValueError("Negative ECONOMY price")

        except Exception as e:
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error=f"נתונים לא תקינים בשלב 2: {e}"
            )

        with db_conn() as cur:
            cur.execute(
                "SELECT size FROM aircraft WHERE aircraft_id_number = ?;",
                (aircraft_id_number,)
            )
            row = cur.fetchone()

        if not row:
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error="מטוס לא נמצא במערכת."
            )

        aircraft_size_real = (row["size"] or "").upper()

        if selected_size and aircraft_size_real != selected_size:
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error="בחירת המטוס לא תואמת לגודל שנבחר בשלב 1. חזור ובחר מטוס מתאים."
            )

        if long_required and aircraft_size_real == "SMALL":
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error="טיסה ארוכה (מעל 6 שעות) מחייבת מטוס LARGE. אי אפשר ליצור טיסה עם SMALL."
            )

        req = required_crew_counts(aircraft_size_real)
        if len(pilots_ids) != req["pilots"] or len(attendants_ids) != req["attendants"]:
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error=f"כמות צוות לא תקינה. למטוס {aircraft_size_real} צריך {req['pilots']} טייסים ו-{req['attendants']} דיילים."
            )

        pilots_available_ids = {int(p["id_number"]) for p in (pilots_list or [])}
        attendants_available_ids = {int(a["id_number"]) for a in (attendants_list or [])}

        if not set(pilots_ids).issubset(pilots_available_ids):
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error="נבחר טייס שאינו זמין בזמן הטיסה. חזור ובחר טייסים זמינים."
            )

        if not set(attendants_ids).issubset(attendants_available_ids):
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error="נבחר דייל שאינו זמין בזמן הטיסה. חזור ובחר דיילים זמינים."
            )

        class_prices = {"ECONOMY": price_econ}
        if aircraft_size_real == "LARGE":
            try:
                if price_bus_raw is None or price_bus_raw == "":
                    raise ValueError("חובה למלא מחיר BUSINESS במטוס גדול.")
                price_bus = float(price_bus_raw)
                if price_bus < 0:
                    raise ValueError("מחיר BUSINESS לא יכול להיות שלילי.")
            except Exception as e:
                return render_step2(
                    origin=origin,
                    destination=destination,
                    aircraft_size_selected=selected_size,
                    dep_date=dep_date,
                    dep_time=dep_time,
                    duration=int(duration),
                    arrival_dt=arrival_dt,
                    long_required=long_required,
                    aircraft_list=aircraft_list,
                    pilots_list=pilots_list,
                    attendants_list=attendants_list,
                    generated_flight_number=generated_flight_number,
                    error=str(e)
                )

            class_prices["BUSINESS"] = price_bus

        try:
            create_flight_with_crew_and_prices(
                flight_number=flight_number,
                aircraft_id_number=aircraft_id_number,
                origin_airport=origin,
                destination_airport=destination,
                departure_dt=departure_dt,
                pilots_ids=pilots_ids,
                attendants_ids=attendants_ids,
                class_prices=class_prices
            )
        except Exception as e:
            return render_step2(
                origin=origin,
                destination=destination,
                aircraft_size_selected=selected_size,
                dep_date=dep_date,
                dep_time=dep_time,
                duration=int(duration),
                arrival_dt=arrival_dt,
                long_required=long_required,
                aircraft_list=aircraft_list,
                pilots_list=pilots_list,
                attendants_list=attendants_list,
                generated_flight_number=generated_flight_number,
                error=f"שגיאה ביצירת טיסה: {e}"
            )

        return render_template(
            "manager_add_flight.html",
            airports=airports,
            message=f"הטיסה {flight_number:04d} נוצרה בהצלחה "
        )

    origin = (request.form.get("origin_airport") or "").strip().upper()
    destination = (request.form.get("destination_airport") or "").strip().upper()
    dep_date = (request.form.get("departure_date") or "").strip()
    dep_time = (request.form.get("departure_time") or "").strip()

    selected_size = (request.form.get("aircraft_size") or "").strip().upper()

    if not (origin and destination and dep_date and dep_time and selected_size):
        return render_template(
            "manager_add_flight.html",
            airports=airports,
            error="חובה לבחור מקור, יעד, גודל מטוס, תאריך ושעה.",
            origin_selected=origin,
            destination_selected=destination,
            aircraft_size_selected=selected_size,
            departure_date=dep_date,
            departure_time=dep_time
        )

    if origin == destination:
        return render_template(
            "manager_add_flight.html",
            airports=airports,
            error="שדה מקור ושדה יעד לא יכולים להיות זהים.",
            origin_selected=origin,
            destination_selected=destination,
            aircraft_size_selected=selected_size,
            departure_date=dep_date,
            departure_time=dep_time
        )

    try:
        departure_dt = datetime.strptime(f"{dep_date} {dep_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return render_template(
            "manager_add_flight.html",
            airports=airports,
            error="תאריך/שעה לא תקינים.",
            origin_selected=origin,
            destination_selected=destination,
            aircraft_size_selected=selected_size,
            departure_date=dep_date,
            departure_time=dep_time
        )

    if departure_dt < datetime.now():
        return render_template(
            "manager_add_flight.html",
            airports=airports,
            error="לא ניתן לבחור תאריך/שעה שכבר עברו.",
            origin_selected=origin,
            destination_selected=destination,
            aircraft_size_selected=selected_size,
            departure_date=dep_date,
            departure_time=dep_time
        )

    duration = get_flight_duration_minutes(origin, destination)
    if duration is None:
        return render_template(
            "manager_add_flight.html",
            airports=airports,
            error=f"קו הטיסה שנבחר לא קיים במערכת: {origin} → {destination}",
            origin_selected=origin,
            destination_selected=destination,
            aircraft_size_selected=selected_size,
            departure_date=dep_date,
            departure_time=dep_time
        )

    long_required = is_long_flight(int(duration))

    if long_required and selected_size == "SMALL":
        return render_template(
            "manager_add_flight.html",
            airports=airports,
            error="טיסה ארוכה (מעל 6 שעות) מחייבת מטוס LARGE. בחרת SMALL ולכן אי אפשר להמשיך.",
            origin_selected=origin,
            destination_selected=destination,
            aircraft_size_selected=selected_size,
            departure_date=dep_date,
            departure_time=dep_time
        )

    arrival_dt = departure_dt + timedelta(minutes=int(duration))

    aircraft_list = get_available_aircraft(departure_dt, arrival_dt, origin, long_required)
    aircraft_list = [a for a in (aircraft_list or []) if (a["size"] or "").upper() == selected_size]

    pilots_list = get_available_pilots(departure_dt, arrival_dt, origin, long_required)
    attendants_list = get_available_attendants(departure_dt, arrival_dt, origin, long_required)

    if not aircraft_list:
        return render_template(
            "manager_add_flight.html",
            airports=airports,
            error=f"אין מטוס פנוי מתאים בגודל {selected_size} בתאריך/שעה שנבחרו.",
            origin_selected=origin,
            destination_selected=destination,
            aircraft_size_selected=selected_size,
            departure_date=dep_date,
            departure_time=dep_time
        )

    if long_required:
        if len(pilots_list) < 3 or len(attendants_list) < 6:
            return render_template(
                "manager_add_flight.html",
                airports=airports,
                error="אין מספיק אנשי צוות זמינים לטיסה ארוכה (צריך לפחות 3 טייסים ו-6 דיילים).",
                origin_selected=origin,
                destination_selected=destination,
                aircraft_size_selected=selected_size,
                departure_date=dep_date,
                departure_time=dep_time
            )
    else:
        if len(pilots_list) < 2 or len(attendants_list) < 3:
            return render_template(
                "manager_add_flight.html",
                airports=airports,
                error="אין מספיק אנשי צוות זמינים לטיסה (צריך לפחות 2 טייסים ו-3 דיילים).",
                origin_selected=origin,
                destination_selected=destination,
                aircraft_size_selected=selected_size,
                departure_date=dep_date,
                departure_time=dep_time
            )

    generated_flight_number = generate_unique_flight_number()

    return render_template(
        "manager_add_flight_step2.html",
        origin=origin,
        destination=destination,
        aircraft_size_selected=selected_size,
        dep_date=dep_date,
        dep_time=dep_time,
        duration=duration,
        arrival_dt=arrival_dt,
        long_required=long_required,
        aircraft_list=aircraft_list,
        pilots_list=pilots_list,
        attendants_list=attendants_list,
        generated_flight_number=generated_flight_number,
        req=required_crew_counts(selected_size)
    )


@app.route("/select_seats_guest", methods=["POST"])
def select_seats(): #Show seat selection for a guest available seats per class and taken seats
    flight_number = int(request.form.get("flight_number"))

    flight = get_flight_with_aircraft(flight_number)
    if not flight:
        return "Flight not found", 404

    aircraft_id = flight["aircraft_id_number"]
    classes = get_classes_for_aircraft(aircraft_id)

    seats_by_class = {}
    for c in classes:
        seats_by_class[c["type"]] = get_seats_for_flight_class(flight_number, c["type"])

    taken = get_taken_seats_for_flight(flight_number)

    return render_template(
        "select_seats_guest.html",
        flight=flight,
        classes=classes,
        seats_by_class=seats_by_class,
        taken=taken
    )


@app.route("/review_order", methods=["POST"])
def review_order(): #Create order summary validate seats calculate total and save pending order in session
    flight_number = int(request.form.get("flight_number"))
    seats_json = request.form.get("selected_seats_json") or "[]"

    try:
        selected = json.loads(seats_json)
    except Exception:
        return "נתוני מושבים לא תקינים", 400

    if not selected:
        return "לא נבחרו מושבים", 400

    flight = get_flight_with_aircraft(flight_number)

    if not flight:
        return "Flight not found", 404

    aircraft_id = flight["aircraft_id_number"]
    seats_details = []
    total = 0.0

    for s in selected:
        with db_conn() as cur:
            cur.execute(
                """
                SELECT `price`
                FROM `seats_in_flights`
                WHERE `aircraft_id_number` = ?
                  AND `flight_number` = ?
                  AND `class_type` = ?
                  AND `row_number` = ?
                  AND `column_number` = ?
                """,
                (aircraft_id, flight_number, str(s.get("class_type")).upper(), s.get("row_number"),
                 s.get("column_number"))
            )
            r = cur.fetchone()

        if r:
            price = float(r["price"] or 0)
            total += price
            seats_details.append({
                "class_type": s.get("class_type"),
                "row_number": s.get("row_number"),
                "column_number": s.get("column_number"),
                "price": price
            })
    session["pending_flight_number"] = flight_number
    session["pending_seats_json"] = seats_json
    session["pending_total"] = total

    return render_template(
        "review_order.html",
        flight=flight,
        seats=seats_details,
        total=total,
        selected_seats_json=seats_json
    )

@app.route("/place_order", methods=["GET"])
def place_order(): #Show guest checkout form prefill email if exists
    if not session.get("pending_flight_number") or not session.get("pending_seats_json"):
        return redirect("/flight_search_guest")
    pref_email = session.get("user_email")
    return render_template("place_order.html", pref_email=pref_email)

@app.route("/place_order_post", methods=["POST"])
def place_order_post(): #Collect guest customer details and save them in session before payment
    flight_number = session.get("pending_flight_number")
    seats_json = session.get("pending_seats_json")

    if not flight_number or not seats_json:
        return redirect("/flight_search_guest")

    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone_main = (request.form.get("phone_main") or "").strip()
    extra_phones = request.form.getlist("extra_phones[]")

    phones = [phone_main] if phone_main else []
    phones += [p.strip() for p in extra_phones if (p or "").strip()]

    passport = (request.form.get("passport") or "").strip()
    birth_date = (request.form.get("birth_date") or "").strip()

    if not first_name or not last_name or not email or len(phones) == 0:
        return render_template("place_order.html", error="חובה למלא שם פרטי, שם משפחה, אימייל ולפחות טלפון אחד.")

    session["pending_customer"] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phones": phones,
        "passport": passport,
        "birth_date": birth_date
    }

    return redirect(url_for("payment"))

@app.route("/place_order_customer_post", methods=["POST"])
def place_order_customer_post(): #Start customer checkout verify login and pending order then redirect to customer payment
    if not session.get("user_email"):
        return redirect(url_for("login"))
    if not session.get("pending_flight_number") or not session.get("pending_seats_json"):
        return redirect(url_for("flight_search_customers"))
    return redirect(url_for("payment_customer"))


@app.route("/place_order_customer", methods=["GET"])
def place_order_customer(): #Load logged in customer profile and open the customer order page
    if not session.get("user_email"):
        return redirect(url_for("login"))

    if not session.get("pending_flight_number") or not session.get("pending_seats_json"):
        return redirect(url_for("flight_search_customers"))

    email = session["user_email"]

    with db_conn() as cur:
        cur.execute("""
            SELECT email, first_name, last_name
            FROM customer
            WHERE email = ?
        """, (email,))
        customer = cur.fetchone()

        cur.execute("""
            SELECT phone_number
            FROM customer_phone_number
            WHERE email = ?
            ORDER BY phone_number
        """, (email,))

        raw_phones = cur.fetchall() or []
        phones = []
        for r in raw_phones:
            p_str = str(r["phone_number"]).strip()
            if p_str and not p_str.startswith('0'):
                p_str = '0' + p_str
            phones.append(p_str)

    if not customer:
        return redirect(url_for("flight_search_customers"))

    profile = {
        "first_name": customer["first_name"],
        "last_name": customer["last_name"],
        "email": customer["email"],
        "phones": phones
    }

    session["pending_customer"] = profile
    return render_template("place_order_customer.html", profile=profile)


@app.route("/review_order_customer", methods=["POST"])
def review_order_customer(): #Create customer order summary calculate total and save pending order in session
    if not session.get("user_email"):
        return redirect(url_for("login"))

    flight_number = int(request.form.get("flight_number"))
    seats_json = request.form.get("selected_seats_json") or "[]"

    try:
        selected = json.loads(seats_json)
    except Exception:
        return "נתוני מושבים לא תקינים", 400

    if not selected:
        return "לא נבחרו מושבים", 400

    flight = get_flight_with_aircraft(flight_number)
    if not flight:
        return "Flight not found", 404

    aircraft_id = flight["aircraft_id_number"]

    seats_details = []
    total = 0.0

    for s in selected:
        with db_conn() as cur:
            cur.execute(
                """
                SELECT `price`
                FROM `seats_in_flights`
                WHERE `aircraft_id_number` = ?
                  AND `flight_number` = ?
                  AND `class_type` = ?
                  AND `row_number` = ?
                  AND `column_number` = ?
                """,
                (aircraft_id, flight_number, str(s.get("class_type")).upper(),
                 s.get("row_number"), s.get("column_number"))
            )
            r = cur.fetchone()

        if r:
            price = float(r["price"] or 0)
            total += price
            seats_details.append({
                "class_type": s.get("class_type"),
                "row_number": s.get("row_number"),
                "column_number": s.get("column_number"),
                "price": price
            })

    session["pending_flight_number"] = flight_number
    session["pending_seats_json"] = seats_json
    session["pending_total"] = total

    return render_template(
        "review_order_customer.html",
        flight=flight,
        seats=seats_details,
        total=total,
        selected_seats_json=seats_json
    )


@app.route("/confirm_seats", methods=["POST"])
def confirm_seats(): #Confirm seats and create a reservation
    email = (request.form.get("email") or "").strip().lower()
    flight_number = int(request.form.get("flight_number"))
    seats_json = request.form.get("selected_seats_json") or "[]"
    if not email:
        return "חובה להכניס אימייל", 400

    seats = json.loads(seats_json)
    if not seats:
        return "לא נבחרו מושבים", 400

    try:
        reservation_code = create_reservation_with_seats(email, flight_number, seats)
    except Exception as e:
        flight = get_flight_with_aircraft(flight_number)
        aircraft_id = flight["aircraft_id_number"]
        classes = get_classes_for_aircraft(aircraft_id)
        seats_by_class = {c["type"]: get_seats_for_aircraft_class(aircraft_id, c["type"]) for c in classes}
        taken = get_taken_seats_for_flight(flight_number)

        return render_template(
            "select_seats_customer.html",
            flight=flight,
            classes=classes,
            seats_by_class=seats_by_class,
            taken=taken,
            error=str(e)
        )

    return render_template("reservation_success.html", reservation_code=reservation_code, email=email)

@app.route("/manager_reports", methods=["GET"])
def manager_reports(): #Show manager reports page and run the selected report image and table preview
    report_id = request.args.get("report", "1").strip()

    report_map = {
        "1": ("ממוצע נצילות טיסות שהתקיימו", report_avg_occupancy),
        "2": ("הכנסות לפי גודל מטוס / יצרנית / מחלקה", report_revenue_by_combo),
        "3": ("שעות טיסה מצטברות לעובדים (לפי טיסה קצרה/ארוכה)", report_staff_hours),
        "4": ("שיעור ביטולי רכישות לפי חודש", report_cancellation_rate),
        "5": ("סיכום פעילות חודשית לכל מטוס", report_aircraft_monthly_summary),
    }

    title, fn = report_map.get(report_id, report_map["1"])
    img_path, df = fn()

    table_rows = []
    table_cols = []
    if df is not None and not df.empty:
        table_cols = list(df.columns)
        table_rows = df.head(50).to_dict(orient="records")

    return render_template(
        "manager_reports.html",
        report_id=report_id,
        title=title,
        img_path=img_path,
        table_cols=table_cols,
        table_rows=table_rows
    )


@app.route("/select_seats_customer", methods=["POST"])
def select_seats_customer(): #Show seat selection for a logged in customer available seats per class and taken seats
    flight_number = int(request.form.get("flight_number"))
    flight = get_flight_with_aircraft(flight_number)
    if not flight:
        return "Flight not found", 404
    aircraft_id = flight["aircraft_id_number"]
    classes = get_classes_for_aircraft(aircraft_id)
    seats_by_class = {}
    for c in classes:
        seats_by_class[c["type"]] = get_seats_for_flight_class(flight_number, c["type"])
    taken = get_taken_seats_for_flight(flight_number)

    return render_template(
        "select_seats_customer.html",
        flight=flight,
        classes=classes,
        seats_by_class=seats_by_class,
        taken=taken
    )

@app.route("/payment_guest", methods=["GET"])
def payment(): #Show guest payment page using pending order from session
    if not session.get("pending_flight_number") or not session.get("pending_seats_json") or not session.get("pending_customer"):
        return redirect(url_for("flight_search_guest"))
    total = session.get("pending_total")
    email = (session.get("pending_customer") or {}).get("email")
    return render_template("payment_guest.html", total=total, email=email)


@app.route("/payment_post", methods=["POST"])
def payment_post(): #Validate payment details create guest reservation and clear pending session data
    flight_number = session.get("pending_flight_number")
    seats_json = session.get("pending_seats_json")
    cust = session.get("pending_customer")

    if not flight_number or not seats_json or not cust:
        return redirect(url_for("flight_search_guest"))

    card_name = (request.form.get("card_name") or "").strip()
    card_number = str(request.form.get("card_number") or "").strip().replace(" ", "")
    exp = (request.form.get("exp") or "").strip()
    cvv = str(request.form.get("cvv") or "").strip()

    if not card_name or not card_number or not exp or not cvv:
        return render_template("payment_guest.html", error="חובה למלא את כל פרטי האשראי.", total=session.get("pending_total"), email=cust.get("email"))

    if (not card_number.isdigit()) or not (12 <= len(card_number) <= 19):
        return render_template("payment_guest.html", error="מספר כרטיס לא תקין.", total=session.get("pending_total"), email=cust.get("email"))

    if (not cvv.isdigit()) or (len(cvv) not in (3, 4)):
        return render_template("payment_guest.html", error="CVV לא תקין.", total=session.get("pending_total"), email=cust.get("email"))

    ok, exp_err = is_card_exp_valid(exp)
    if not ok:
        return render_template(
            "payment_guest.html",
            error=exp_err,
            total=session.get("pending_total"),
            email=cust.get("email")
        )

    selected = json.loads(seats_json)

    try:
        reservation_code = create_reservation_with_seats_with_customer_details(
            email=cust["email"],
            first_name=cust["first_name"],
            last_name=cust["last_name"],
            phones=cust["phones"],
            flight_number=int(flight_number),
            seats=selected
        )
    except Exception as e:
        return render_template("payment_guest.html", error=str(e), total=session.get("pending_total"), email=cust.get("email")), 409

    session.pop("pending_flight_number", None)
    session.pop("pending_seats_json", None)
    session.pop("pending_total", None)
    session.pop("pending_customer", None)

    return redirect(url_for("payment_success", reservation_code=reservation_code))

@app.route("/payment_customer", methods=["GET"])
def payment_customer(): #Show customer payment page using pending order from session
    if not session.get("user_email"):
        return redirect(url_for("login"))

    if not session.get("pending_flight_number") or not session.get("pending_seats_json"):
        return redirect(url_for("flight_search_customers"))

    total = session.get("pending_total")
    email = session.get("user_email")
    return render_template("payment_customer.html", total=total, email=email)


@app.route("/payment_customer_post", methods=["POST"])
def payment_customer_post(): #Validate customer payment details create reservation and clear pending session data
    if not session.get("user_email"):
        return redirect(url_for("login"))

    flight_number = session.get("pending_flight_number")
    seats_json = session.get("pending_seats_json")

    if not flight_number or not seats_json:
        return redirect(url_for("flight_search_customers"))

    email = session.get("user_email")

    with db_conn() as cur:
        cur.execute("""
            SELECT email, first_name, last_name
            FROM customer
            WHERE email = ?
            LIMIT 1;
        """, (email,))
        customer = cur.fetchone()

        cur.execute("""
            SELECT phone_number
            FROM customer_phone_number
            WHERE email = ?
            ORDER BY phone_number;
        """, (email,))
        phones = [r["phone_number"] for r in (cur.fetchall() or [])]

    if not customer:
        return redirect(url_for("flight_search_customers"))

    customer = dict(customer)
    profile = {
        "email": customer["email"],
        "first_name": customer.get("first_name"),
        "last_name": customer.get("last_name"),
        "phones": phones
    }

    card_name = (request.form.get("card_name") or "").strip()
    card_number = str(request.form.get("card_number") or "").strip().replace(" ", "")
    exp = (request.form.get("exp") or "").strip()
    cvv = str(request.form.get("cvv") or "").strip()

    if not card_name or not card_number or not exp or not cvv:
        return render_template(
            "payment_customer.html",
            error="חובה למלא את כל פרטי האשראי.",
            total=session.get("pending_total"),
            email=email
        )

    if (not card_number.isdigit()) or not (12 <= len(card_number) <= 19):
        return render_template(
            "payment_customer.html",
            error="מספר כרטיס לא תקין.",
            total=session.get("pending_total"),
            email=email
        )

    if (not cvv.isdigit()) or (len(cvv) not in (3, 4)):
        return render_template(
            "payment_customer.html",
            error="CVV לא תקין.",
            total=session.get("pending_total"),
            email=email
        )
    ok, exp_err = is_card_exp_valid(exp)
    if not ok:
        return render_template(
            "payment_customer.html",
            error=exp_err,
            total=session.get("pending_total"),
            email=email
        )

    try:
        selected = json.loads(seats_json)
    except Exception:
        return render_template(
            "payment_customer.html",
            error="בחירת מושבים לא תקינה.",
            total=session.get("pending_total"),
            email=email
        ), 400

    try:
        reservation_code = create_reservation_with_seats_with_customer_details(
            email=profile["email"],
            first_name=profile["first_name"],
            last_name=profile["last_name"],
            phones=profile["phones"],
            flight_number=int(flight_number),
            seats=selected
        )
    except Exception as e:
        return render_template(
            "payment_customer.html",
            error=str(e),
            total=session.get("pending_total"),
            email=email
        ), 409

    session.pop("pending_flight_number", None)
    session.pop("pending_seats_json", None)
    session.pop("pending_total", None)

    return redirect(url_for("payment_success_customer", reservation_code=reservation_code))

@app.route("/payment_success", methods=["GET"])
def payment_success(): #Show guest payment success page with reservation code
    reservation_code = request.args.get("reservation_code")
    return render_template("payment_success_guest.html", reservation_code=reservation_code)


@app.route("/payment_success_customer", methods=["GET"])
def payment_success_customer(): #Show customer payment success page with reservation code
    reservation_code = request.args.get("reservation_code")
    return render_template("payment_success_customer.html", reservation_code=reservation_code)


if __name__ == '__main__':
    app.run(debug=True)