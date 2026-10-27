import io
import csv
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, Response, make_response
from flask_login import login_required
from app.models import db, Student, SessionSchedule, AttendanceRecord

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    """Attendance reports generator with daily, weekly, and monthly scopes."""
    today = date.today()

    time_frame = request.args.get('time_frame', 'today')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    section = request.args.get('section', '').strip()
    course_grade = request.args.get('course_grade', '').strip()
    status = request.args.get('status', '').strip()
    session_id = request.args.get('session_id', type=int)

    if time_frame == 'today':
        start_date = today
        end_date = today
    elif time_frame == 'weekly':
        start_date = today - timedelta(days=6)
        end_date = today
    elif time_frame == 'monthly':
        start_date = today - timedelta(days=29)
        end_date = today
    elif time_frame == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today
            end_date = today
    else:
        start_date = today
        end_date = today

    query = AttendanceRecord.query.filter(
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date
    )

    if session_id:
        query = query.filter_by(session_id=session_id)
    if status:
        query = query.filter_by(status=status)
    if section or course_grade:
        query = query.join(Student)
        if section:
            query = query.filter(Student.section == section)
        if course_grade:
            query = query.filter(Student.course_grade == course_grade)

    records = query.order_by(AttendanceRecord.date.desc(), AttendanceRecord.timestamp.desc()).all()

    total_count = len(records)
    total_present = sum(1 for r in records if r.status == 'Present')
    total_late = sum(1 for r in records if r.status == 'Late')
    total_absent = sum(1 for r in records if r.status == 'Absent')

    sections = [s[0] for s in db.session.query(Student.section).distinct().all() if s[0]]
    courses = [c[0] for c in db.session.query(Student.course_grade).distinct().all() if c[0]]
    sessions = SessionSchedule.query.filter_by(is_active=True).all()

    return render_template(
        'reports/index.html',
        records=records,
        total_count=total_count,
        total_present=total_present,
        total_late=total_late,
        total_absent=total_absent,
        time_frame=time_frame,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        section=section,
        course_grade=course_grade,
        status=status,
        session_id=session_id,
        sections=sections,
        courses=courses,
        sessions=sessions
    )

@reports_bp.route('/export/csv')
@login_required
def export_csv():
    """Generates and downloads a clean CSV report based on current filters."""
    time_frame = request.args.get('time_frame', 'today')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    section = request.args.get('section', '').strip()
    course_grade = request.args.get('course_grade', '').strip()
    status = request.args.get('status', '').strip()
    session_id = request.args.get('session_id', type=int)

    today = date.today()
    if time_frame == 'today':
        start_date = end_date = today
    elif time_frame == 'weekly':
        start_date = today - timedelta(days=6)
        end_date = today
    elif time_frame == 'monthly':
        start_date = today - timedelta(days=29)
        end_date = today
    elif time_frame == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date = today
    else:
        start_date = end_date = today

    query = AttendanceRecord.query.filter(
        AttendanceRecord.date >= start_date,
        AttendanceRecord.date <= end_date
    )
    if session_id:
        query = query.filter_by(session_id=session_id)
    if status:
        query = query.filter_by(status=status)
    if section or course_grade:
        query = query.join(Student)
        if section:
            query = query.filter(Student.section == section)
        if course_grade:
            query = query.filter(Student.course_grade == course_grade)

    records = query.order_by(AttendanceRecord.date.desc(), AttendanceRecord.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Record ID', 'Student ID', 'Student Name', 'Year Level', 'Course', 'Section',
        'Session', 'Date', 'Time Scanned', 'Status', 'Method', 'Recorded By', 'Remarks'
    ])

    for r in records:
        writer.writerow([
            r.id,
            r.student.student_id if r.student else '',
            r.student.full_name if r.student else '',
            r.student.year_level if r.student else '',
            r.student.course_grade if r.student else '',
            r.student.section if r.student else '',
            r.session.name if r.session else '',
            r.date.strftime('%Y-%m-%d'),
            r.timestamp.strftime('%I:%M:%S %p'),
            r.status,
            r.scan_method,
            r.scanner.full_name if r.scanner else 'System',
            r.remarks or ''
        ])

    csv_data = output.getvalue()
    filename = f"attendance_report_{start_date}_to_{end_date}.csv"

    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response
