from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='patient')  # 'patient', 'clinician', or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.now)

    profile = db.relationship('PatientProfile', backref='user', uselist=False)


class PatientProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    name = db.Column(db.String(255))  # Full name (first + last)
    age = db.Column(db.Integer)
    sex = db.Column(db.String(16))
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    
    def get_full_name(self):
        """Get full name from first and last name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.name:
            return self.name
        return None


class GlucoseReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now, index=True)
    glucose = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(32), default='manual')  # manual, cgm, forecast


class RiskPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    probability = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(512), nullable=False)
    level = db.Column(db.String(16), default='info')  # info, warning, high
    created_at = db.Column(db.DateTime, default=datetime.now)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for system events
    action = db.Column(db.String(100), nullable=False)  # e.g., 'user_login', 'user_register', 'prediction_made', etc.
    details = db.Column(db.Text)  # JSON or text details
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    
    user = db.relationship('User', backref='audit_logs')

