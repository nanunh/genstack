from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import secrets
from database import get_db_connection

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = secrets.token_urlsafe(32)  # Generate a random secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def create_user(name: str, email: str, password: str) -> dict:
    """Create a new user"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "message": "Database connection failed"}
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return {"success": False, "message": "Email already registered"}
        
        # Hash password and create user
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, password_hash)
        )
        connection.commit()
        
        user_id = cursor.lastrowid
        
        # Generate token
        token = create_access_token({"user_id": user_id, "email": email})
        
        cursor.close()
        connection.close()
        
        return {
            "success": True,
            "message": "User created successfully",
            "token": token,
            "user": {"id": user_id, "name": name, "email": email}
        }
        
    except Exception as e:
        if connection:
            connection.close()
        return {"success": False, "message": f"Error creating user: {str(e)}"}

def authenticate_user(email: str, password: str) -> dict:
    """Authenticate a user"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "message": "Database connection failed"}
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get user by email
        cursor.execute(
            "SELECT id, name, email, password_hash, is_active FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        
        if not user:
            return {"success": False, "message": "Invalid email or password"}
        
        if not user['is_active']:
            return {"success": False, "message": "Account is disabled"}
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            return {"success": False, "message": "Invalid email or password"}
        
        # Update last login
        cursor.execute(
            "UPDATE users SET last_login = NOW() WHERE id = %s",
            (user['id'],)
        )
        connection.commit()
        
        # Generate token
        token = create_access_token({"user_id": user['id'], "email": user['email']})
        
        cursor.close()
        connection.close()
        
        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {"id": user['id'], "name": user['name'], "email": user['email']}
        }
        
    except Exception as e:
        if connection:
            connection.close()
        return {"success": False, "message": f"Error authenticating user: {str(e)}"}

def get_user_from_token(token: str) -> Optional[dict]:
    """Get user info from JWT token"""
    payload = verify_token(token)
    if not payload:
        return None
    
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email FROM users WHERE id = %s AND is_active = TRUE",
            (payload.get('user_id'),)
        )
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        return user
    except Exception as e:
        if connection:
            connection.close()
        return None