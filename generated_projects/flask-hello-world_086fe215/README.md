# Flask Hello World Application

A simple Flask application that displays a personalized "Hello World" message with the user's name.

## Features

- Simple web interface with HTML, CSS, and JavaScript
- User can enter their name to get a personalized greeting
- RESTful API endpoint for greeting functionality
- Responsive design

## Installation

1. Clone this repository
2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

The application will be available at http://127.0.0.1:5000/

## Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── static/                # Static files
│   ├── css/
│   │   └── style.css      # CSS styles
│   └── js/
│       └── script.js      # JavaScript code
└── templates/
    └── index.html         # HTML template
```

## API Endpoints

- `POST /greet` - Accepts a JSON payload with a "name" field and returns a personalized greeting

## License

MIT