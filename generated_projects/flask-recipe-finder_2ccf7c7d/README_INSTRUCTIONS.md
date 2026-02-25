# flask-recipe-finder - Instructions

**Project ID:** 2ccf7c7d-119a-43a3-90b3-21c5c5a95adf
**Created:** 2025-10-30T12:53:18.184314

## Setup and Run Instructions

# Recipe Finder Application Setup Instructions

## Local Development Setup

1. Clone the repository to your local machine

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

5. Create a `.env` file based on the `.env.example` template:
   ```
   cp .env.example .env
   ```

6. Edit the `.env` file and add your Spoonacular API key (get one from https://spoonacular.com/food-api)

7. Initialize the database:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

8. Run the application:
   ```
   flask run
   ```

9. Access the application at http://localhost:5000

## Docker Setup

1. Make sure Docker and Docker Compose are installed on your system

2. Create a `.env` file as described above

3. Build and start the container:
   ```
   docker-compose up -d
   ```

4. Access the application at http://localhost:5000

## Default Admin Account

On first run, the application creates a default admin account:
- Username: admin
- Password: adminpassword

You should change this password after first login.

## Features

- Search for recipes by ingredients you have
- View detailed recipe instructions
- Save favorite recipes
- Admin dashboard with user management and analytics

Enjoy your Recipe Finder application!