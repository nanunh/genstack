# Hindu Calendar Application

A web application that displays a Hindu calendar with Rahu Kalam and Yamakandam timings for each day.

## Features

- Monthly calendar view with navigation
- Display of Rahu Kalam and Yamakandam timings for each day
- Detailed information about these auspicious/inauspicious periods
- Responsive design for desktop and mobile devices

## Technologies Used

- Backend: Python Flask
- Frontend: HTML, CSS, JavaScript
- Dependencies: Flask, pytz

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd hindu-calendar-app
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Understanding Rahu Kalam and Yamakandam

In Hindu astrology, certain periods of the day are considered inauspicious for starting new activities:

### Rahu Kalam
- Monday: 7:30 AM - 9:00 AM
- Tuesday: 3:00 PM - 4:30 PM
- Wednesday: 12:00 PM - 1:30 PM
- Thursday: 1:30 PM - 3:00 PM
- Friday: 10:30 AM - 12:00 PM
- Saturday: 9:00 AM - 10:30 AM
- Sunday: 4:30 PM - 6:00 PM

### Yamakandam
- Monday: 10:30 AM - 12:00 PM
- Tuesday: 9:00 AM - 10:30 AM
- Wednesday: 7:30 AM - 9:00 AM
- Thursday: 6:00 AM - 7:30 AM
- Friday: 3:00 PM - 4:30 PM
- Saturday: 1:30 PM - 3:00 PM
- Sunday: 12:00 PM - 1:30 PM

## License

This project is licensed under the MIT License - see the LICENSE file for details.
