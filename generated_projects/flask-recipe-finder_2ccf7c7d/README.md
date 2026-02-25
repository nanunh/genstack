# Recipe Finder Application

A web application built with Flask and JavaScript that allows users to search for recipes based on ingredients they have, view detailed instructions, and save their favorite recipes.

## Features

### User Features
- Search for recipes by ingredients
- View detailed recipe instructions and information
- Save favorite recipes for easy access
- User authentication (register, login, logout)

### Admin Features
- Manage registered users
- View application analytics
- Track popular recipes and user activity

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLAlchemy with SQLite
- **API Integration**: Spoonacular Food API
- **Authentication**: Flask-Login

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository
   ```
   git clone https://github.com/yourusername/recipe-finder.git
   cd recipe-finder
   ```

2. Create a virtual environment
   ```
   python -m venv venv
   ```

3. Activate the virtual environment
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

4. Install dependencies
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root (copy from `.env.example`)
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///recipes.db
   SPOONACULAR_API_KEY=your-api-key-here
   ```

   > Note: You'll need to get a free API key from [Spoonacular API](https://spoonacular.com/food-api)

6. Initialize the database
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

7. Run the application
   ```
   flask run
   ```

8. Access the application at `http://localhost:5000`

## Default Admin Account

On first run, the application creates a default admin account:
- Username: admin
- Password: adminpassword

It's recommended to change this password after first login.

## License

MIT
