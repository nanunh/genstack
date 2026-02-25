from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_cors import CORS
from flask_caching import Cache
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///recipes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
CORS(app)

# Configure caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Spoonacular API key
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')
SPOONACULAR_BASE_URL = 'https://api.spoonacular.com'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    favorites = db.relationship('Favorite', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, nullable=False)
    recipe_title = db.Column(db.String(200), nullable=False)
    recipe_image = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # search, view, favorite
    details = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='activities')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# API Routes
@app.route('/api/search', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def search_recipes():
    ingredients = request.args.get('ingredients', '')
    if not ingredients:
        return jsonify({'error': 'No ingredients provided'}), 400
    
    if not SPOONACULAR_API_KEY:
        return jsonify({'error': 'API key not configured'}), 500
    
    # Log user activity if logged in
    if current_user.is_authenticated:
        activity = UserActivity(user_id=current_user.id, activity_type='search', details=ingredients)
        db.session.add(activity)
        db.session.commit()
    
    # Call Spoonacular API
    params = {
        'apiKey': SPOONACULAR_API_KEY,
        'ingredients': ingredients,
        'number': 10,
        'ranking': 1,
        'ignorePantry': False
    }
    
    try:
        response = requests.get(f'{SPOONACULAR_BASE_URL}/recipes/findByIngredients', params=params)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipe/<int:recipe_id>', methods=['GET'])
@cache.cached(timeout=600)
def get_recipe(recipe_id):
    if not SPOONACULAR_API_KEY:
        return jsonify({'error': 'API key not configured'}), 500
    
    # Log user activity if logged in
    if current_user.is_authenticated:
        activity = UserActivity(user_id=current_user.id, activity_type='view', details=f'Recipe {recipe_id}')
        db.session.add(activity)
        db.session.commit()
    
    # Call Spoonacular API
    params = {'apiKey': SPOONACULAR_API_KEY}
    
    try:
        response = requests.get(f'{SPOONACULAR_BASE_URL}/recipes/{recipe_id}/information', params=params)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/favorites', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_favorites():
    if request.method == 'GET':
        favorites = Favorite.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': fav.id,
            'recipe_id': fav.recipe_id,
            'recipe_title': fav.recipe_title,
            'recipe_image': fav.recipe_image,
            'created_at': fav.created_at.isoformat()
        } for fav in favorites])
    
    elif request.method == 'POST':
        data = request.get_json()
        recipe_id = data.get('recipe_id')
        recipe_title = data.get('recipe_title')
        recipe_image = data.get('recipe_image')
        
        if not recipe_id or not recipe_title:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if already favorited
        existing = Favorite.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
        if existing:
            return jsonify({'error': 'Recipe already in favorites'}), 400
        
        favorite = Favorite(recipe_id=recipe_id, recipe_title=recipe_title, 
                           recipe_image=recipe_image, user_id=current_user.id)
        db.session.add(favorite)
        
        # Log activity
        activity = UserActivity(user_id=current_user.id, activity_type='favorite', 
                               details=f'Added recipe {recipe_id} to favorites')
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({'message': 'Recipe added to favorites', 'id': favorite.id})
    
    elif request.method == 'DELETE':
        data = request.get_json()
        recipe_id = data.get('recipe_id')
        
        if not recipe_id:
            return jsonify({'error': 'Missing recipe_id'}), 400
        
        favorite = Favorite.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
        if not favorite:
            return jsonify({'error': 'Recipe not in favorites'}), 404
        
        db.session.delete(favorite)
        db.session.commit()
        
        return jsonify({'message': 'Recipe removed from favorites'})

# Admin routes
@app.route('/api/admin/users', methods=['GET'])
@login_required
def admin_users():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat()
    } for user in users])

@app.route('/api/admin/analytics', methods=['GET'])
@login_required
def admin_analytics():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get activity counts by type
    search_count = UserActivity.query.filter_by(activity_type='search').count()
    view_count = UserActivity.query.filter_by(activity_type='view').count()
    favorite_count = UserActivity.query.filter_by(activity_type='favorite').count()
    
    # Get user count
    user_count = User.query.count()
    
    # Get favorite recipe counts
    favorite_recipes = db.session.query(Favorite.recipe_id, Favorite.recipe_title, 
                                      db.func.count(Favorite.id).label('count'))\
                                .group_by(Favorite.recipe_id)\
                                .order_by(db.desc('count'))\
                                .limit(10).all()
    
    return jsonify({
        'user_count': user_count,
        'activity_counts': {
            'search': search_count,
            'view': view_count,
            'favorite': favorite_count
        },
        'popular_recipes': [{
            'recipe_id': recipe[0],
            'recipe_title': recipe[1],
            'favorite_count': recipe[2]
        } for recipe in favorite_recipes]
    })

# Auth routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    login_user(user)
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin
        }
    })

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/user', methods=['GET'])
@login_required
def get_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'is_admin': current_user.is_admin
    })

# Serve frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join('static', path)):
        return app.send_static_file(path)
    return app.send_static_file('index.html')

# Create admin user function
def create_admin():
    if User.query.filter_by(is_admin=True).first() is None:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('adminpassword')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()  # Call the function directly within app context
    app.run(debug=True)