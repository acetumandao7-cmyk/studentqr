import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    os.makedirs(app.config['QR_FOLDER'], exist_ok=True)

    with app.app_context():
        try:
            db.create_all()
            admin = User.query.filter((User.username == 'admin') | (User.email == 'admin@school.edu')).first()
            if not admin:
                admin = User(
                    username='admin',
                    full_name='System Administrator',
                    email='admin@school.edu',
                    role='Administrator',
                    is_active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
        except Exception:
            db.session.rollback()

    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.attendance.routes import attendance_bp
    from app.reports.routes import reports_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('attendance.teacher_dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/verify/<token>')
    def verify_student(token):
        from datetime import datetime, date
        from flask import render_template, request
        from app.models import db, Student, AttendanceRecord, SessionSchedule, SystemLog
        from app.utils import check_duplicate_attendance

        student = Student.query.filter(
            (Student.qr_code_token == token) | (Student.student_id == token)
        ).first_or_404()

        today = date.today()
        now = datetime.now()
        current_time = now.time()

        scan_result = None

        if student.status == 'Active':
            active_sessions = SessionSchedule.query.filter_by(is_active=True).all()
            target_session = None
            for s in active_sessions:
                if s.start_time <= current_time <= s.end_time:
                    target_session = s
                    break

            if not target_session and active_sessions:
                target_session = active_sessions[0]

            if target_session:
                is_duplicate, existing = check_duplicate_attendance(student.id, target_session.id, today)
                if is_duplicate:
                    scan_result = {
                        'is_new': False,
                        'status': existing.status,
                        'time_str': existing.timestamp.strftime('%I:%M %p'),
                        'session_name': target_session.name,
                        'message': f"Already Checked In! Marked as {existing.status} at {existing.timestamp.strftime('%I:%M %p')} today."
                    }
                else:
                    status = target_session.determine_status(current_time)
                    new_record = AttendanceRecord(
                        student_id=student.id,
                        session_id=target_session.id,
                        date=today,
                        timestamp=now,
                        status=status,
                        scanned_by=student.teacher_id,
                        scan_method='QR_SCAN',
                        remarks='Mobile QR Attendance Scan'
                    )
                    db.session.add(new_record)
                    db.session.commit()

                    SystemLog.log(
                        action='ATTENDANCE_SCAN',
                        details=f'Mobile QR scan for {student.full_name} ({student.student_id}) marked as {status}',
                        user_id=student.teacher_id,
                        ip_address=request.remote_addr
                    )

                    scan_result = {
                        'is_new': True,
                        'status': status,
                        'time_str': now.strftime('%I:%M %p'),
                        'session_name': target_session.name,
                        'message': f"Attendance Successfully Logged! Marked as {status} for {target_session.name}."
                    }

        total_present = student.attendances.filter_by(status='Present').count()
        total_late = student.attendances.filter_by(status='Late').count()
        total_absent = student.attendances.filter_by(status='Absent').count()
        total_scans = total_present + total_late + total_absent

        rate = round(((total_present + total_late) / total_scans * 100), 1) if total_scans > 0 else 100.0
        recent_records = student.attendances.order_by(AttendanceRecord.timestamp.desc()).limit(10).all()

        return render_template(
            'public/student_card.html',
            student=student,
            scan_result=scan_result,
            total_present=total_present,
            total_late=total_late,
            total_absent=total_absent,
            total_scans=total_scans,
            rate=rate,
            recent_records=recent_records
        )

    return app
