import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from forms import LoginForm, AnalysisRequestForm
from email_service import EmailService
from ai_analyzer import AIAnalyzer

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-for-testing')
csrf = CSRFProtect(app)

# Initialize services
email_service = EmailService()
ai_analyzer = AIAnalyzer()

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Try to connect to email server
        try:
            email_service.connect(
                username=form.email.data,
                password=form.password.data,
                server=form.server.data,
                port=form.port.data
            )
            session['logged_in'] = True
            session['email'] = form.email.data
            session['server'] = form.server.data
            session['port'] = form.port.data
            session['password'] = form.password.data  # Note: In production, use more secure methods
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/fetch-emails')
def fetch_emails():
    if 'logged_in' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Reconnect to ensure the connection is fresh
        email_service.connect(
            username=session['email'],
            password=session['password'],
            server=session['server'],
            port=session['port']
        )
        
        # Fetch emails (default to inbox and last 10 emails)
        folder = request.args.get('folder', 'INBOX')
        limit = int(request.args.get('limit', 10))
        emails = email_service.fetch_emails(folder=folder, limit=limit)
        
        return jsonify(emails)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-email', methods=['POST'])
def analyze_email():
    if 'logged_in' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    form = AnalysisRequestForm()
    if form.validate_on_submit():
        email_id = form.email_id.data
        analysis_type = form.analysis_type.data
        
        try:
            # Reconnect to ensure the connection is fresh
            email_service.connect(
                username=session['email'],
                password=session['password'],
                server=session['server'],
                port=session['port']
            )
            
            # Get the full email content
            email_content = email_service.get_email_content(email_id)
            
            # Analyze the email
            analysis_result = ai_analyzer.analyze_email(
                email_content=email_content,
                analysis_type=analysis_type
            )
            
            return jsonify(analysis_result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid form data'}), 400

@app.route('/folders')
def get_folders():
    if 'logged_in' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Reconnect to ensure the connection is fresh
        email_service.connect(
            username=session['email'],
            password=session['password'],
            server=session['server'],
            port=session['port']
        )
        
        folders = email_service.list_folders()
        return jsonify(folders)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_ENV') == 'development')
