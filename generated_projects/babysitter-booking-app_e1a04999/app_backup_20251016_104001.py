from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///babysitter.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(10), nullable=False)  # 'parent' or 'sitter'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sitter_profile = db.relationship('SitterProfile', backref='user', uselist=False)
    parent_bookings = db.relationship('Booking', backref='parent', foreign_keys='Booking.parent_id')
    sitter_bookings = db.relationship('Booking', backref='sitter', foreign_keys='Booking.sitter_id')
    reviews_given = db.relationship('Review', backref='reviewer', foreign_keys='Review.reviewer_id')
    reviews_received = db.relationship('Review', backref='reviewed', foreign_keys='Review.reviewed_id')

class SitterProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bio = db.Column(db.Text)
    experience = db.Column(db.Text)
    hourly_rate = db.Column(db.Float)
    availability = db.Column(db.Text)  # JSON string of availability

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sitter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'))
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    booking = db.relationship('Booking')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        user_type = request.form.get('user_type')
        
        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            name=name,
            user_type=user_type
        )
        
        db.session.add(new_user)
        
        # If user is a sitter, create a sitter profile
        if user_type == 'sitter':
            sitter_profile = SitterProfile(user=new_user)
            db.session.add(sitter_profile)
            
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))
        
        login_user(user)
        
        if user.user_type == 'parent':
            return redirect(url_for('parent_dashboard'))
        else:
            return redirect(url_for('sitter_dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/parent/dashboard')
@login_required
def parent_dashboard():
    if current_user.user_type != 'parent':
        return redirect(url_for('index'))
    
    # Get all sitters
    sitters = User.query.filter_by(user_type='sitter').all()
    
    # Get parent's bookings
    bookings = Booking.query.filter_by(parent_id=current_user.id).order_by(Booking.start_time.desc()).all()
    
    return render_template('parent_dashboard.html', sitters=sitters, bookings=bookings)

@app.route('/sitter/dashboard')
@login_required
def sitter_dashboard():
    if current_user.user_type != 'sitter':
        return redirect(url_for('index'))
    
    # Get sitter's profile
    profile = current_user.sitter_profile
    
    # Get sitter's bookings
    bookings = Booking.query.filter_by(sitter_id=current_user.id).order_by(Booking.start_time.desc()).all()
    
    return render_template('sitter_dashboard.html', profile=profile, bookings=bookings)

@app.route('/sitter/profile', methods=['GET', 'POST'])
@login_required
def sitter_profile():
    if current_user.user_type != 'sitter':
        return redirect(url_for('index'))
    
    profile = current_user.sitter_profile
    
    if request.method == 'POST':
        profile.bio = request.form.get('bio')
        profile.experience = request.form.get('experience')
        profile.hourly_rate = float(request.form.get('hourly_rate'))
        profile.availability = request.form.get('availability')
        
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('sitter_dashboard'))
    
    return render_template('sitter_profile.html', profile=profile)

@app.route('/sitter/<int:sitter_id>')
@login_required
def view_sitter(sitter_id):
    sitter = User.query.filter_by(id=sitter_id, user_type='sitter').first_or_404()
    reviews = Review.query.filter_by(reviewed_id=sitter_id).all()
    
    return render_template('view_sitter.html', sitter=sitter, reviews=reviews)

@app.route('/book/<int:sitter_id>', methods=['GET', 'POST'])
@login_required
def book_sitter(sitter_id):
    if current_user.user_type != 'parent':
        return redirect(url_for('index'))
    
    sitter = User.query.filter_by(id=sitter_id, user_type='sitter').first_or_404()
    
    if request.method == 'POST':
        start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        
        booking = Booking(
            parent_id=current_user.id,
            sitter_id=sitter.id,
            start_time=start_time,
            end_time=end_time
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Booking request sent!')
        return redirect(url_for('parent_dashboard'))
    
    return render_template('book_sitter.html', sitter=sitter)

@app.route('/booking/<int:booking_id>/update', methods=['POST'])
@login_required
def update_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure the user is authorized to update this booking
    if current_user.user_type == 'sitter' and booking.sitter_id == current_user.id:
        action = request.form.get('action')
        
        if action == 'accept':
            booking.status = 'accepted'
        elif action == 'reject':
            booking.status = 'rejected'
        
        db.session.commit()
        flash(f'Booking {booking.status}!')
    
    return redirect(url_for('sitter_dashboard'))

@app.route('/booking/<int:booking_id>/review', methods=['GET', 'POST'])
@login_required
def review_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure the user is authorized to review this booking
    if booking.parent_id != current_user.id or booking.status != 'completed':
        return redirect(url_for('parent_dashboard'))
    
    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')
        
        review = Review(
            reviewer_id=current_user.id,
            reviewed_id=booking.sitter_id,
            booking_id=booking.id,
            rating=rating,
            comment=comment
        )
        
        db.session.add(review)
        db.session.commit()
        
        flash('Review submitted!')
        return redirect(url_for('parent_dashboard'))
    
    return render_template('review_booking.html', booking=booking)

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)