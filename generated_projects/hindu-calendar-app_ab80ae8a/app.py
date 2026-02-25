from flask import Flask, render_template, jsonify
import datetime
import pytz

app = Flask(__name__)

# Rahu and Yamakandam timings calculation
def get_rahu_yamakandam(date):
    # Day of week (0 is Monday, 6 is Sunday)
    day_of_week = date.weekday()
    
    # Rahu Kalam timings based on day of week (traditional calculation)
    rahu_timings = {
        0: ("7:30 AM", "9:00 AM"),  # Monday
        1: ("3:00 PM", "4:30 PM"),  # Tuesday
        2: ("12:00 PM", "1:30 PM"), # Wednesday
        3: ("1:30 PM", "3:00 PM"),  # Thursday
        4: ("10:30 AM", "12:00 PM"), # Friday
        5: ("9:00 AM", "10:30 AM"), # Saturday
        6: ("4:30 PM", "6:00 PM")   # Sunday
    }
    
    # Yamakandam timings based on day of week (traditional calculation)
    yamakandam_timings = {
        0: ("10:30 AM", "12:00 PM"), # Monday
        1: ("9:00 AM", "10:30 AM"),  # Tuesday
        2: ("7:30 AM", "9:00 AM"),   # Wednesday
        3: ("6:00 AM", "7:30 AM"),   # Thursday
        4: ("3:00 PM", "4:30 PM"),   # Friday
        5: ("1:30 PM", "3:00 PM"),   # Saturday
        6: ("12:00 PM", "1:30 PM")   # Sunday
    }
    
    return {
        "rahu": rahu_timings[day_of_week],
        "yamakandam": yamakandam_timings[day_of_week]
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/calendar/<int:year>/<int:month>')
def get_calendar(year, month):
    # Get the first day of the month
    first_day = datetime.datetime(year, month, 1)
    
    # Get the number of days in the month
    if month == 12:
        last_day = datetime.datetime(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.datetime(year, month + 1, 1) - datetime.timedelta(days=1)
    
    num_days = last_day.day
    
    # Get the day of the week for the first day (0 is Monday, 6 is Sunday)
    first_day_of_week = first_day.weekday()
    
    # Create calendar data
    calendar_data = []
    
    for day in range(1, num_days + 1):
        current_date = datetime.datetime(year, month, day)
        timings = get_rahu_yamakandam(current_date)
        
        calendar_data.append({
            "day": day,
            "rahu": timings["rahu"],
            "yamakandam": timings["yamakandam"]
        })
    
    return jsonify({
        "year": year,
        "month": month,
        "first_day_of_week": first_day_of_week,
        "days": calendar_data
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)