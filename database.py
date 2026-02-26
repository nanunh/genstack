import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'stackgpt_db'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def create_database_and_tables():
    """Create database and required tables if they don't exist"""
    try:
        # Connect without database first
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = connection.cursor()
        
        # Create database if not exists
        db_name = os.getenv('DB_NAME', 'stackgpt_db')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_email (email)
            )
        """)
        
        # Create sessions table (optional, for session management)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(500) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_token (token)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_assistant_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                project_id VARCHAR(255) NOT NULL,
                project_name VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                sender ENUM('user', 'assistant', 'system') NOT NULL,
                message_type VARCHAR(50) DEFAULT 'text',
                metadata JSON DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_project_id (project_id),
                INDEX idx_user_project (user_id, project_id),
                INDEX idx_created_at (created_at)
            )
        """)
        
        # Create password reset tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_token (token)
            )
        """)

        connection.commit()
        print("✅ Database and tables created successfully!")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"❌ Error creating database/tables: {e}")

# Initialize database on import
create_database_and_tables()