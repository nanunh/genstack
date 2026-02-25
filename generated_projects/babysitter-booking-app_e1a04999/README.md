# BabySitter Booking Application

A Flask web application that connects parents with babysitters. Parents can find, book, and review sitters, while sitters can create profiles, set their availability, and accept booking requests.

## Features

### For Parents
- Create an account
- Browse available sitters
- View sitter profiles and reviews
- Book sitters for specific dates and times
- Leave reviews after completed bookings

### For Sitters
- Create a profile with bio, experience, and hourly rate
- Set availability
- Accept or decline booking requests
- View upcoming and past bookings

## Technology Stack

- **Backend**: Python with Flask framework
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Frontend**: HTML, CSS, JavaScript

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Run the application:
   ```
   python app.py
   ```
6. Open your browser and navigate to `http://localhost:5000`

## Database Schema

- **User**: Stores both parent and sitter user accounts
- **SitterProfile**: Additional information for sitter users
- **Booking**: Booking requests and appointments
- **Review**: Ratings and comments from parents about sitters

## Future Enhancements

- Payment integration
- Real-time messaging between parents and sitters
- Calendar integration for availability management
- Background check verification for sitters
- Mobile app version

## License

MIT License