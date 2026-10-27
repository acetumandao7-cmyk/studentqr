from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.Enum('Administrator', 'Teacher', name='user_roles'), nullable=False, default='Teacher')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scanned_attendances = db.relationship('AttendanceRecord', backref='scanner', lazy='dynamic')
    logs = db.relationship('SystemLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'Administrator'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }

class SessionSchedule(db.Model):
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    late_threshold_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attendances = db.relationship('AttendanceRecord', backref='session', lazy='dynamic')

    def determine_status(self, current_time: time) -> str:
        """Determines if the scan is Present or Late based on threshold"""
        if current_time <= self.late_threshold_time:
            return 'Present'
        return 'Late'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'start_time': self.start_time.strftime('%H:%M:%S') if self.start_time else '',
            'late_threshold_time': self.late_threshold_time.strftime('%H:%M:%S') if self.late_threshold_time else '',
            'end_time': self.end_time.strftime('%H:%M:%S') if self.end_time else '',
            'is_active': self.is_active
        }

class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.Enum('Male', 'Female', 'Other', name='student_gender'), nullable=False, default='Male')
    year_level = db.Column(db.String(20), nullable=False, default='1st Year')
    course_grade = db.Column(db.String(100), nullable=False, index=True)
    section = db.Column(db.String(50), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    subject = db.Column(db.String(100), nullable=True)
    class_time = db.Column(db.String(100), nullable=True)
    guardian_name = db.Column(db.String(100), nullable=True)
    guardian_contact = db.Column(db.String(30), nullable=True)
    qr_code_token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    qr_image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('Active', 'Inactive', name='student_status'), nullable=False, default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = db.relationship('User', backref=db.backref('assigned_students', lazy='dynamic'))
    attendances = db.relationship('AttendanceRecord', backref='student', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'gender': self.gender,
            'year_level': self.year_level,
            'course_grade': self.course_grade,
            'section': self.section,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.full_name if self.teacher else None,
            'subject': self.subject,
            'class_time': self.class_time,
            'guardian_name': self.guardian_name,
            'guardian_contact': self.guardian_contact,
            'qr_code_token': self.qr_code_token,
            'qr_image_path': self.qr_image_path,
            'status': self.status
        }

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'session_id', 'date', name='unique_student_session_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.Enum('Present', 'Late', 'Absent', name='attendance_status'), nullable=False, default='Present', index=True)
    scanned_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    scan_method = db.Column(db.Enum('QR_SCAN', 'MANUAL_OVERRIDE', name='scan_methods'), nullable=False, default='QR_SCAN')
    remarks = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_code': self.student.student_id if self.student else None,
            'student_name': self.student.full_name if self.student else None,
            'course_grade': self.student.course_grade if self.student else None,
            'section': self.student.section if self.student else None,
            'session_name': self.session.name if self.session else None,
            'date': self.date.strftime('%Y-%m-%d'),
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'time_only': self.timestamp.strftime('%I:%M:%S %p'),
            'status': self.status,
            'scan_method': self.scan_method,
            'scanned_by_user': self.scanner.full_name if self.scanner else 'System',
            'remarks': self.remarks or ''
        }

class SystemLog(db.Model):
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @classmethod
    def log(cls, action: str, details: str = None, user_id: int = None, ip_address: str = None):
        try:
            entry = cls(
                action=action,
                details=details,
                user_id=user_id,
                ip_address=ip_address
            )
            db.session.add(entry)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
