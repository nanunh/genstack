# Flask Login Page

A simple login page built with Python Flask.

## Features

- User login with email and password
- Session management
- Flash messages for notifications
- Client-side form validation
- Responsive design

## Installation

1. Clone this repository
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

## Usage

1. Run the application:
   ```
   python app.py
   ```
2. Open your browser and navigate to `http://127.0.0.1:5000`
3. Use the following credentials to log in:
   - Email: `user@example.com`
   - Password: `password123`

## Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── static/                # Static files
│   ├── css/
│   │   └── style.css      # CSS styles
│   └── js/
│       └── script.js      # JavaScript for client-side validation
└── templates/             # HTML templates
    ├── login.html         # Login page template
    └── dashboard.html     # Dashboard page template
```

## Security Notes

This is a simple demonstration application. For a production environment, consider the following security enhancements:

1. Use a proper database instead of the in-memory dictionary
2. Hash passwords using a secure algorithm like bcrypt
3. Implement CSRF protection
4. Use HTTPS
5. Add rate limiting for login attempts
