# FlyTAU

FlyTAU is a web based flight booking and management system built with Python and Flask.
The website allows users to search for flights, select seats, and create reservations.  
Both registered customers and guests can book flights, while registered customers can also view and manage their reservation history.
Managers can manage the system by adding flights, assigning aircraft and crew, canceling flights, and viewing operational reports and statistics.
The system uses an SQLite database and server-side rendered HTML pages to handle all business logic and data processing.

## Technologies Used
- Python
- Flask
- SQLite
- Pandas
- Matplotlib
- HTML / Jinja Templates

## Project Structure (Main Files)
- `main.py` – Flask routes and application logic
- `utils.py` – Database access and business logic
- `utils_reports.py` – SQL queries and report generation
- `templates/` – HTML templates
- `static/` – Static files (CSS, images, reports)

## How to Run the Project
1. Make sure Python is installed
2. Install required packages:
   ```bash
   pip install flask pandas matplotli