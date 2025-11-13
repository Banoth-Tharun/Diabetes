import os
import io
import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from ml.model import ModelService
from ml.federated_model import FederatedModelService
from ml.explain import explain_prediction
from ml.forecast import forecast_glucose

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'app.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database
from models import db, User, PatientProfile, GlucoseReading, RiskPrediction, Alert, AuditLog

db.init_app(app)

# Auth
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Template filter for local time formatting
@app.template_filter('localtime')
def localtime_filter(dt):
    """Convert datetime to local time string"""
    if dt is None:
        return ''
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# Helper function to get user display name
def get_user_display_name(user):
    """Get display name for user (name if available, else email)"""
    if user.role == 'patient' and user.profile:
        name = user.profile.get_full_name()
        if name:
            return name
    return user.email

# Make helper available in templates
@app.context_processor
def utility_processor():
    return dict(get_user_display_name=get_user_display_name)

# RBAC helpers

def role_required(*roles):
    def decorator(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Unauthorized', 'error')
                return redirect(url_for('index'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'clinician':
        return redirect(url_for('clinician_dashboard'))
    return redirect(url_for('patient_dashboard'))


def log_audit(user_id, action, details=None, ip_address=None):
    """Helper function to log audit events"""
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address or request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f'Error logging audit: {e}')
        db.session.rollback()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            log_audit(user.id, 'user_login', f'User {email} logged in', request.remote_addr)
            return redirect(url_for('index'))
        log_audit(None, 'login_failed', f'Failed login attempt for {email}', request.remote_addr)
        flash('Invalid credentials', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        # Force role to patient - no role selection for new users
        role = 'patient'
        
        # Validation
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        # Get name fields
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validation for names
        if not first_name or not last_name:
            flash('First name and last name are required', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login instead.', 'error')
            return redirect(url_for('login'))
        
        # Create new user (always as patient)
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role='patient'
        )
        db.session.add(user)
        db.session.flush()  # Flush to get user.id
        
        # Create patient profile with name
        full_name = f"{first_name} {last_name}"
        profile = PatientProfile(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            name=full_name
        )
        db.session.add(profile)
        
        db.session.commit()
        
        log_audit(user.id, 'user_register', f'New patient registered: {email}', request.remote_addr)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    log_audit(current_user.id, 'user_logout', f'User {current_user.email} logged out', request.remote_addr)
    logout_user()
    return redirect(url_for('login'))


@app.route('/patient')
@login_required
@role_required('patient')
def patient_dashboard():
    readings = GlucoseReading.query.filter_by(user_id=current_user.id).order_by(GlucoseReading.timestamp.desc()).limit(100).all()
    predictions = RiskPrediction.query.filter_by(user_id=current_user.id).order_by(RiskPrediction.created_at.desc()).limit(20).all()
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at.desc()).limit(10).all()
    return render_template('patient_dashboard.html', readings=readings, predictions=predictions, alerts=alerts)


@app.route('/clinician')
@login_required
@role_required('clinician')
def clinician_dashboard():
    patients = User.query.filter_by(role='patient').all()
    latest_predictions = {p.id: RiskPrediction.query.filter_by(user_id=p.id).order_by(RiskPrediction.created_at.desc()).first() for p in patients}
    return render_template('clinician_dashboard.html', patients=patients, latest_predictions=latest_predictions)


@app.route('/clinician/export/<int:patient_id>/csv')
@login_required
@role_required('clinician')
def export_patient_csv(patient_id: int):
    readings = GlucoseReading.query.filter_by(user_id=patient_id).order_by(GlucoseReading.timestamp.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'glucose'])
    for r in readings:
        writer.writerow([r.timestamp.isoformat(), r.glucose])
    mem = io.BytesIO(output.getvalue().encode('utf-8'))
    mem.seek(0)
    filename = f'patient_{patient_id}_glucose.csv'
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')


# API: Predict
@app.post('/api/predict')
@login_required
def api_predict():
    payload = request.get_json(force=True)
    # Try federated model first, fallback to regular model
    federated_service = FederatedModelService()
    if federated_service.is_available():
        model_service = federated_service
    else:
        model_service = ModelService()
    pred, prob, features_order = model_service.predict(payload)

    rp = RiskPrediction(user_id=current_user.id, prediction=int(pred), probability=float(prob))
    db.session.add(rp)
    db.session.commit()

    # simple alert rule
    if prob >= 0.7:
        alert = Alert(user_id=current_user.id, message=f'High diabetes risk: {prob:.2f}', level='high')
        db.session.add(alert)
        db.session.commit()

    log_audit(current_user.id, 'prediction_made', f'Risk prediction: {pred}, probability: {prob:.2f}', request.remote_addr)
    return jsonify({'prediction': int(pred), 'probability': float(prob), 'features': features_order})


# API: Explain
@app.post('/api/explain')
@login_required
def api_explain():
    payload = request.get_json(force=True)
    model_service = ModelService()
    pred, prob, features_order = model_service.predict(payload)
    shap_values = explain_prediction(model_service.model, payload, features_order)
    return jsonify({'prediction': int(pred), 'probability': float(prob), 'shap_values': shap_values, 'features': features_order})


# API: Forecast
@app.post('/api/forecast')
@login_required
def api_forecast():
    data: Dict[str, Any] = {}
    cgm_uploaded = False
    
    if request.is_json:
        data = request.get_json()
    elif 'file' in request.files:
        file = request.files['file']
        text = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))
        readings = []
        for row in reader:
            readings.append({
                'timestamp': row.get('timestamp'),
                'glucose': float(row.get('glucose', '0') or 0)
            })
        data = {'readings': readings}
        cgm_uploaded = True
        
        # Store CGM readings in database
        for reading in readings:
            try:
                # Parse timestamp
                ts_str = reading.get('timestamp')
                if isinstance(ts_str, str):
                    # Try ISO format first
                    try:
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    except:
                        # Try other common formats
                        try:
                            ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                        except:
                            ts = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S')
                else:
                    ts = datetime.now()
                
                # Check if reading already exists (avoid duplicates)
                existing = GlucoseReading.query.filter_by(
                    user_id=current_user.id,
                    timestamp=ts,
                    source='cgm'
                ).first()
                
                if not existing:
                    glucose_reading = GlucoseReading(
                        user_id=current_user.id,
                        timestamp=ts,
                        glucose=float(reading.get('glucose', 0)),
                        source='cgm'
                    )
                    db.session.add(glucose_reading)
            except Exception as e:
                print(f'Error storing CGM reading: {e}')
                continue
        
        db.session.commit()
        log_audit(current_user.id, 'cgm_uploaded', f'CGM data uploaded: {len(readings)} readings', request.remote_addr)
    else:
        return jsonify({'error': 'No data provided'}), 400

    readings = data.get('readings', [])
    if not readings:
        # fallback to last readings from DB
        db_readings = GlucoseReading.query.filter_by(user_id=current_user.id).order_by(GlucoseReading.timestamp.desc()).limit(50).all()
        readings = [{'timestamp': r.timestamp.isoformat(), 'glucose': r.glucose} for r in reversed(db_readings)]

    forecast_points = forecast_glucose(readings)
    # cache latest forecast points as readings
    now = datetime.now()
    for pt in forecast_points:
        ts = datetime.fromisoformat(pt['timestamp']) if isinstance(pt['timestamp'], str) else now
        db.session.add(GlucoseReading(user_id=current_user.id, timestamp=ts, glucose=float(pt['glucose']), source='forecast'))
    db.session.commit()

    return jsonify({'forecast': forecast_points, 'cgm_stored': cgm_uploaded})


@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    # Get statistics
    total_users = User.query.count()
    total_patients = User.query.filter_by(role='patient').count()
    total_clinicians = User.query.filter_by(role='clinician').count()
    total_admins = User.query.filter_by(role='admin').count()
    
    # Get recent audit logs
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    
    # Get all users for management
    users = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('admin_dashboard.html', 
                         total_users=total_users,
                         total_patients=total_patients,
                         total_clinicians=total_clinicians,
                         total_admins=total_admins,
                         audit_logs=audit_logs,
                         users=users)


@app.route('/admin/create-clinician', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_clinician():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validation
        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Create clinician user
        clinician = User(
            email=email,
            password_hash=generate_password_hash(password),
            role='clinician'
        )
        db.session.add(clinician)
        db.session.commit()
        
        log_audit(current_user.id, 'clinician_created', f'Admin created clinician: {email}', request.remote_addr)
        flash(f'Clinician {email} created successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_dashboard'))
    
    email = user.email
    db.session.delete(user)
    db.session.commit()
    
    log_audit(current_user.id, 'user_deleted', f'Admin deleted user: {email}', request.remote_addr)
    flash(f'User {email} deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


# Database migration helper
def migrate_database():
    """Add new columns to existing database if they don't exist"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        
        # Check if patient_profile table exists
        if 'patient_profile' in table_names:
            columns = [col['name'] for col in inspector.get_columns('patient_profile')]
            
            # Check if first_name and last_name columns exist
            if 'first_name' not in columns:
                try:
                    db.session.execute(text('ALTER TABLE patient_profile ADD COLUMN first_name VARCHAR(100)'))
                    db.session.commit()
                    print('Added first_name column to patient_profile')
                except Exception as e:
                    db.session.rollback()
                    print(f'Error adding first_name column: {e}')
            
            if 'last_name' not in columns:
                try:
                    db.session.execute(text('ALTER TABLE patient_profile ADD COLUMN last_name VARCHAR(100)'))
                    db.session.commit()
                    print('Added last_name column to patient_profile')
                except Exception as e:
                    db.session.rollback()
                    print(f'Error adding last_name column: {e}')
        
        # Note: audit_log table will be created by db.create_all() if it doesn't exist
    except Exception as e:
        print(f'Migration check failed (this is OK if database is new): {e}')

# CLI helper to init DB and seed users
@app.cli.command('initdb')
def initdb():
    with app.app_context():
        db.create_all()
        migrate_database()
        seed_defaults()
        print('Initialized the database and seeded defaults.')


def seed_defaults():
    # Create admin user
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(email='admin@example.com', role='admin', password_hash=generate_password_hash('admin123'))
        db.session.add(admin)
        print('Created admin user: admin@example.com / admin123')
    
    # Create default clinician
    if not User.query.filter_by(email='clinician@example.com').first():
        clinician = User(email='clinician@example.com', role='clinician', password_hash=generate_password_hash('password123'))
        db.session.add(clinician)
    
    # Create default patient
    if not User.query.filter_by(email='patient@example.com').first():
        patient = User(email='patient@example.com', role='patient', password_hash=generate_password_hash('password123'))
        db.session.add(patient)
        db.session.flush()
        # Create profile for default patient if it doesn't exist
        if not patient.profile:
            profile = PatientProfile(
                user_id=patient.id,
                first_name='John',
                last_name='Doe',
                name='John Doe'
            )
            db.session.add(profile)
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_database()
        seed_defaults()
    app.run(host='127.0.0.1', port=5000, debug=True)
