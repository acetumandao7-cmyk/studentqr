from datetime import datetime, date, time, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.models import db, Student, SessionSchedule, AttendanceRecord, SystemLog
from app.utils import check_duplicate_attendance, get_client_ip

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    ph_tz = timezone(timedelta(hours=8))
    today = datetime.now(ph_tz).date()
    active_sessions = SessionSchedule.query.filter_by(is_active=True).order_by(SessionSchedule.start_time.asc()).all()
    selected_session_id = request.args.get('session_id', type=int)

    base_query = AttendanceRecord.query.filter_by(date=today)
    if selected_session_id:
        base_query = base_query.filter_by(session_id=selected_session_id)

    if not current_user.is_admin:
        teacher_students_count = Student.query.filter_by(teacher_id=current_user.id, status='Active').count()
        if teacher_students_count > 0:
            base_query = base_query.join(Student).filter(
                (Student.teacher_id == current_user.id) | (AttendanceRecord.scanned_by == current_user.id)
            )
            total_active_students = teacher_students_count
        else:
            total_active_students = Student.query.filter_by(status='Active').count()
    else:
        total_active_students = Student.query.filter_by(status='Active').count()

    today_records = base_query.order_by(AttendanceRecord.timestamp.desc()).all()
    total_present = sum(1 for r in today_records if r.status == 'Present')
    total_late = sum(1 for r in today_records if r.status == 'Late')
    total_scanned = len(today_records)
    attendance_rate = 0
    if total_active_students > 0:
        attendance_rate = round((total_scanned / total_active_students) * 100, 1)

    return render_template(
        'dashboard/teacher.html',
        today_records=today_records,
        total_present=total_present,
        total_late=total_late,
        total_scanned=total_scanned,
        total_active_students=total_active_students,
        attendance_rate=attendance_rate,
        active_sessions=active_sessions,
        selected_session_id=selected_session_id,
        today_str=today.strftime('%A, %B %d, %Y')
    )

@attendance_bp.route('/scanner')
@login_required
def scanner():
    sessions = SessionSchedule.query.filter_by(is_active=True).order_by(SessionSchedule.start_time.asc()).all()
    default_session = None

    ph_tz = timezone(timedelta(hours=8))
    current_time = datetime.now(ph_tz).time()

    for s in sessions:
        if s.start_time <= current_time <= s.end_time:
            default_session = s
            break

    if not default_session and sessions:
        default_session = sessions[0]

    return render_template(
        'attendance/scanner.html',
        sessions=sessions,
        default_session=default_session
    )

@attendance_bp.route('/api/scan', methods=['POST'])
@login_required
def process_scan():
    data = request.get_json(silent=True) or {}
    qr_payload = data.get('qr_payload', '').strip()
    session_id = data.get('session_id')
    manual_override = bool(data.get('manual_override', False))
    remarks = data.get('remarks', '').strip()

    if not qr_payload:
        return jsonify({
            'success': False,
            'code': 'EMPTY_PAYLOAD',
            'message': 'No QR code payload or Student ID provided.'
        }), 400

    if not session_id:
        return jsonify({
            'success': False,
            'code': 'MISSING_SESSION',
            'message': 'Please select an attendance session.'
        }), 400

    session_obj = SessionSchedule.query.get(session_id)
    if not session_obj or not session_obj.is_active:
        return jsonify({
            'success': False,
            'code': 'INVALID_SESSION',
            'message': 'Selected attendance session is invalid or inactive.'
        }), 400

    if '/verify/' in qr_payload:
        qr_payload = qr_payload.split('/verify/')[-1].strip().split('?')[0].split('/')[0]

    student = Student.query.filter(
        (Student.qr_code_token == qr_payload) | 
        (Student.student_id == qr_payload)
    ).first()

    if not student:
        return jsonify({
            'success': False,
            'code': 'STUDENT_NOT_FOUND',
            'message': f'Unrecognized QR Code. Student record not found.'
        }), 404

    if student.status != 'Active':
        return jsonify({
            'success': False,
            'code': 'STUDENT_INACTIVE',
            'message': f'Student {student.full_name} is marked as Inactive. Contact administrator.'
        }), 403

    ph_tz = timezone(timedelta(hours=8))
    now_ph = datetime.now(ph_tz)
    today = now_ph.date()
    now = now_ph.replace(tzinfo=None)
    current_time = now.time()

    is_duplicate, existing = check_duplicate_attendance(student.id, session_obj.id, today)
    if is_duplicate:
        return jsonify({
            'success': False,
            'code': 'DUPLICATE_ENTRY',
            'message': f'Duplicate Entry! {student.full_name} was already marked {existing.status} at {existing.timestamp.strftime("%I:%M:%S %p")}.',
            'student': student.to_dict(),
            'existing_record': existing.to_dict()
        }), 409

    computed_status = session_obj.determine_status(current_time)
    scan_method = 'MANUAL_OVERRIDE' if manual_override else 'QR_SCAN'

    try:
        new_record = AttendanceRecord(
            student_id=student.id,
            session_id=session_obj.id,
            date=today,
            timestamp=now,
            status=computed_status,
            scanned_by=current_user.id,
            scan_method=scan_method,
            remarks=remarks if remarks else f"Scanned via {scan_method}"
        )
        db.session.add(new_record)
        db.session.commit()

        SystemLog.log(
            action='ATTENDANCE_LOGGED',
            details=f'Attendance recorded for {student.full_name} ({student.student_id}) as {computed_status} in {session_obj.name}',
            user_id=current_user.id,
            ip_address=get_client_ip()
        )

        return jsonify({
            'success': True,
            'code': 'SUCCESS',
            'message': f'Attendance verified! {student.full_name} marked as {computed_status}.',
            'status': computed_status,
            'timestamp': now.strftime('%I:%M:%S %p'),
            'date': today.strftime('%Y-%m-%d'),
            'student': student.to_dict(),
            'session': session_obj.to_dict()
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'code': 'CONCURRENT_DUPLICATE',
            'message': 'Duplicate attendance recorded concurrently by the system.'
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'code': 'SERVER_ERROR',
            'message': f'An error occurred: {str(e)}'
        }), 500

@attendance_bp.route('/api/today-feed')
@login_required
def today_feed():
    ph_tz = timezone(timedelta(hours=8))
    today = datetime.now(ph_tz).date()
    session_id = request.args.get('session_id', type=int)

    query = AttendanceRecord.query.filter_by(date=today)
    if session_id:
        query = query.filter_by(session_id=session_id)

    records = query.order_by(AttendanceRecord.timestamp.desc()).limit(20).all()
    return jsonify({
        'success': True,
        'records': [r.to_dict() for r in records],
        'count': len(records)
    })
