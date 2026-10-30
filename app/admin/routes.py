from pathlib import Path
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.models import db, User, Student, SessionSchedule, AttendanceRecord, SystemLog
from app.utils import role_required, generate_qr_token, create_student_qr_image, get_client_ip

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
@role_required('Administrator')
def admin_guard():
    pass

@admin_bp.route('/dashboard')
def dashboard():
    today = date.today()

    total_students = Student.query.filter_by(status='Active').count()
    total_teachers = User.query.filter_by(role='Teacher', is_active=True).count()

    today_records = AttendanceRecord.query.filter_by(date=today).all()
    today_present = sum(1 for r in today_records if r.status == 'Present')
    today_late = sum(1 for r in today_records if r.status == 'Late')
    today_total_scans = len(today_records)

    attendance_rate = 0
    if total_students > 0:
        attendance_rate = round(((today_present + today_late) / total_students) * 100, 1)

    recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(8).all()
    recent_attendances = AttendanceRecord.query.order_by(AttendanceRecord.timestamp.desc()).limit(7).all()
    active_sessions = SessionSchedule.query.filter_by(is_active=True).all()

    return render_template(
        'dashboard/admin.html',
        total_students=total_students,
        total_teachers=total_teachers,
        today_total_scans=today_total_scans,
        today_present=today_present,
        today_late=today_late,
        attendance_rate=attendance_rate,
        recent_logs=recent_logs,
        recent_attendances=recent_attendances,
        active_sessions=active_sessions,
        today_str=today.strftime('%B %d, %Y')
    )

COURSES_CONFIG = {
    'BSHM': {
        'name': 'BS Hospitality Management',
        'sections': ['BSHM-A', 'BSHM-B', 'BSHM-C', 'BSHM-D', 'BSHM-E'],
        'max_per_course': 40,
        'subjects': [
            'Introduction to Hospitality Management',
            'Food and Beverage Service Operations',
            'Front Office Operations',
            'Housekeeping Operations',
            'Kitchen Operations & Culinary Arts',
            'Bar and Beverage Management',
            'Tourism & Hospitality Marketing',
            'Event Management & Planning',
            'Hospitality Facilities Management',
            'Cost Control in Hospitality'
        ]
    },
    'BSIT': {
        'name': 'BS Information Technology',
        'sections': ['BSIT-A', 'BSIT-B', 'BSIT-C', 'BSIT-D', 'BSIT-E'],
        'max_per_course': 40,
        'subjects': [
            'Introduction to Computing',
            'Computer Programming 1',
            'Computer Programming 2',
            'Data Structures & Algorithms',
            'Database Management Systems',
            'Web Systems and Technologies',
            'Networking & Communications',
            'Information Assurance & Security',
            'Systems Analysis & Design',
            'Mobile Application Development'
        ]
    },
    'BSED': {
        'name': 'BS Education',
        'sections': ['BSED-A', 'BSED-B', 'BSED-C', 'BSED-D', 'BSED-E'],
        'max_per_course': 40,
        'subjects': [
            'Child & Adolescent Learners',
            'Facilitating Learner-Centered Teaching',
            'The Teaching Profession',
            'Assessment of Learning 1',
            'Assessment of Learning 2',
            'Curriculum Development',
            'Educational Technology',
            'Foundations of Special Education',
            'Building & Enhancing New Literacies',
            'Teaching Internship'
        ]
    },
    'BSCS': {
        'name': 'BS Computer Science',
        'sections': ['BSCS-A', 'BSCS-B', 'BSCS-C', 'BSCS-D', 'BSCS-E'],
        'max_per_course': 40,
        'subjects': [
            'Introduction to Computer Science',
            'Discrete Structures',
            'Object-Oriented Programming',
            'Algorithms & Complexity',
            'Computer Architecture & Organization',
            'Operating Systems',
            'Software Engineering',
            'Automata & Language Theory',
            'Artificial Intelligence',
            'Compiler Design'
        ]
    },
    'BSPOLSCI': {
        'name': 'BS Political Science',
        'sections': ['BSPOLSCI-A', 'BSPOLSCI-B', 'BSPOLSCI-C', 'BSPOLSCI-D', 'BSPOLSCI-E'],
        'max_per_course': 40,
        'subjects': [
            'Introduction to Political Science',
            'Philippine Government & Politics',
            'Political Theory & Philosophy',
            'Comparative Politics',
            'International Relations',
            'Public Administration',
            'Constitutional Law',
            'Political Economy',
            'Research in Political Science',
            'Global Politics & Diplomacy'
        ]
    }
}

YEAR_LEVELS = ['1st Year', '2nd Year', '3rd Year', '4th Year']

def generate_next_student_id():
    students = Student.query.filter(Student.student_id.like('ICCT-%')).all()
    max_num = 0
    for s in students:
        parts = s.student_id.split('-')
        if len(parts) >= 2 and parts[1].isdigit():
            num = int(parts[1])
            if num > max_num:
                max_num = num
    return f"ICCT-{max_num + 1:03d}"

def get_courses_summary():
    data = {}
    for code, cfg in COURSES_CONFIG.items():
        total_enrolled = Student.query.filter_by(course_grade=code, status='Active').count()
        sections_data = []
        for sec in cfg['sections']:
            sec_count = Student.query.filter_by(course_grade=code, section=sec, status='Active').count()
            sections_data.append({
                'name': sec,
                'count': sec_count
            })
        data[code] = {
            'name': cfg['name'],
            'max': cfg['max_per_course'],
            'enrolled': total_enrolled,
            'is_full': total_enrolled >= cfg['max_per_course'],
            'sections': sections_data,
            'subjects': cfg.get('subjects', [])
        }
    return data

@admin_bp.route('/students')
def students_list():
    query = Student.query

    search = request.args.get('search', '').strip()
    year_level_filter = request.args.get('year_level', '').strip()
    course_filter = request.args.get('course_grade', '').strip()
    section = request.args.get('section', '').strip()
    status = request.args.get('status', '').strip()

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Student.student_id.ilike(search_fmt)) |
            (Student.first_name.ilike(search_fmt)) |
            (Student.last_name.ilike(search_fmt))
        )
    if year_level_filter:
        query = query.filter_by(year_level=year_level_filter)
    if course_filter:
        query = query.filter_by(course_grade=course_filter)
    if section:
        query = query.filter_by(section=section)
    if status:
        query = query.filter_by(status=status)

    students = query.order_by(Student.student_id.asc()).all()

    courses = list(COURSES_CONFIG.keys())
    all_sections = []
    for code, cfg in COURSES_CONFIG.items():
        all_sections.extend(cfg['sections'])

    return render_template(
        'students/list.html',
        students=students,
        courses=courses,
        sections=all_sections,
        year_levels=YEAR_LEVELS,
        search=search,
        selected_year_level=year_level_filter,
        selected_course=course_filter,
        selected_section=section,
        selected_status=status
    )

@admin_bp.route('/api/enrollment-info')
@login_required
def enrollment_info():
    course_code = request.args.get('course', '').strip()
    data = {}

    if course_code and course_code in COURSES_CONFIG:
        cfg = COURSES_CONFIG[course_code]
        enrolled = Student.query.filter_by(course_grade=course_code, status='Active').count()
        section_counts = {}
        for sec in cfg['sections']:
            count = Student.query.filter_by(course_grade=course_code, section=sec, status='Active').count()
            section_counts[sec] = count
        data = {
            'course': course_code,
            'name': cfg['name'],
            'max': cfg['max_per_course'],
            'enrolled': enrolled,
            'sections': cfg['sections'],
            'section_counts': section_counts
        }
    elif not course_code:
        for code, cfg in COURSES_CONFIG.items():
            enrolled = Student.query.filter_by(course_grade=code, status='Active').count()
            data[code] = {
                'name': cfg['name'],
                'max': cfg['max_per_course'],
                'enrolled': enrolled
            }

    return jsonify(data)

@admin_bp.route('/students/create', methods=['GET', 'POST'])
def student_create():
    courses_data = get_courses_summary()
    active_teachers = User.query.filter_by(role='Teacher', is_active=True).order_by(User.full_name.asc()).all()
    active_sessions = SessionSchedule.query.filter_by(is_active=True).order_by(SessionSchedule.start_time.asc()).all()

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        gender = request.form.get('gender', 'Male')
        year_level = request.form.get('year_level', '1st Year')
        course_grade = request.form.get('course_grade', '').strip()
        section = request.form.get('section', '').strip()
        teacher_id = request.form.get('teacher_id', type=int)
        subject = request.form.get('subject', '').strip()
        custom_subject = request.form.get('custom_subject', '').strip()
        if subject == 'OTHER' and custom_subject:
            subject = custom_subject
        class_time = request.form.get('class_time', '').strip()
        guardian_name = request.form.get('guardian_name', '').strip()
        guardian_contact = request.form.get('guardian_contact', '').strip()

        if not first_name or not last_name or not course_grade or not section:
            flash('All required fields (Name, Course, Section) must be filled.', 'danger')
            return render_template('students/form.html', student=None, next_student_id=generate_next_student_id(),
                                   courses_config=COURSES_CONFIG, courses_data=courses_data, year_levels=YEAR_LEVELS,
                                   teachers=active_teachers, sessions=active_sessions)

        if course_grade in COURSES_CONFIG:
            cfg = COURSES_CONFIG[course_grade]
            enrolled = Student.query.filter_by(course_grade=course_grade, status='Active').count()
            if enrolled >= cfg['max_per_course']:
                flash(f'Course {course_grade} has reached the maximum capacity of {cfg["max_per_course"]} students.', 'danger')
                return render_template('students/form.html', student=None, next_student_id=generate_next_student_id(),
                                       courses_config=COURSES_CONFIG, courses_data=courses_data, year_levels=YEAR_LEVELS,
                                       teachers=active_teachers, sessions=active_sessions)

        student_id = generate_next_student_id()

        qr_token = generate_qr_token(student_id)
        qr_image_rel = create_student_qr_image(qr_token)

        new_student = Student(
            student_id=student_id,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            year_level=year_level,
            course_grade=course_grade,
            section=section,
            teacher_id=teacher_id if teacher_id else None,
            subject=subject if subject else None,
            class_time=class_time if class_time else None,
            guardian_name=guardian_name,
            guardian_contact=guardian_contact,
            qr_code_token=qr_token,
            qr_image_path=qr_image_rel,
            status='Active'
        )

        db.session.add(new_student)
        db.session.commit()

        SystemLog.log(
            action='STUDENT_CREATE',
            details=f'Created student {new_student.full_name} ({new_student.student_id}) with QR token {qr_token}',
            user_id=current_user.id,
            ip_address=get_client_ip()
        )

        flash(f'Student {new_student.full_name} registered as {student_id} with unique QR code!', 'success')
        return redirect(url_for('admin.student_detail', id=new_student.id))

    next_id = generate_next_student_id()
    return render_template('students/form.html', student=None, next_student_id=next_id,
                           courses_config=COURSES_CONFIG, courses_data=courses_data, year_levels=YEAR_LEVELS,
                           teachers=active_teachers, sessions=active_sessions)

@admin_bp.route('/students/<int:id>/edit', methods=['GET', 'POST'])
def student_edit(id):
    student = Student.query.get_or_404(id)
    courses_data = get_courses_summary()
    active_teachers = User.query.filter_by(role='Teacher', is_active=True).order_by(User.full_name.asc()).all()
    active_sessions = SessionSchedule.query.filter_by(is_active=True).order_by(SessionSchedule.start_time.asc()).all()

    if request.method == 'POST':
        student.first_name = request.form.get('first_name', '').strip()
        student.last_name = request.form.get('last_name', '').strip()
        student.gender = request.form.get('gender', 'Male')
        student.year_level = request.form.get('year_level', '1st Year')
        student.course_grade = request.form.get('course_grade', '').strip()
        student.section = request.form.get('section', '').strip()
        teacher_id = request.form.get('teacher_id', type=int)
        student.teacher_id = teacher_id if teacher_id else None
        subject = request.form.get('subject', '').strip()
        custom_subject = request.form.get('custom_subject', '').strip()
        if subject == 'OTHER' and custom_subject:
            subject = custom_subject
        student.subject = subject or None
        student.class_time = request.form.get('class_time', '').strip() or None
        student.guardian_name = request.form.get('guardian_name', '').strip()
        student.guardian_contact = request.form.get('guardian_contact', '').strip()
        student.status = request.form.get('status', 'Active')

        if request.form.get('regenerate_qr'):
            new_token = generate_qr_token(student.student_id)
            new_image = create_student_qr_image(new_token)
            student.qr_code_token = new_token
            student.qr_image_path = new_image
            flash('A new unique QR code has been generated for this student.', 'info')

        db.session.commit()

        SystemLog.log(
            action='STUDENT_UPDATE',
            details=f'Updated student record for {student.full_name} (ID: {student.student_id})',
            user_id=current_user.id,
            ip_address=get_client_ip()
        )

        flash('Student record updated successfully.', 'success')
        return redirect(url_for('admin.student_detail', id=student.id))

    return render_template('students/form.html', student=student,
                           courses_config=COURSES_CONFIG, courses_data=courses_data, year_levels=YEAR_LEVELS,
                           teachers=active_teachers, sessions=active_sessions)

@admin_bp.route('/students/<int:id>')
def student_detail(id):
    student = Student.query.get_or_404(id)
    qr_file = Path(current_app.config['QR_FOLDER']) / f"{student.qr_code_token}.png"
    if not qr_file.exists():
        student.qr_image_path = create_student_qr_image(student.qr_code_token)
        db.session.commit()
    history = student.attendances.order_by(AttendanceRecord.timestamp.desc()).limit(30).all()

    total_present = student.attendances.filter_by(status='Present').count()
    total_late = student.attendances.filter_by(status='Late').count()
    total_absent = student.attendances.filter_by(status='Absent').count()

    return render_template(
        'students/profile.html',
        student=student,
        history=history,
        total_present=total_present,
        total_late=total_late,
        total_absent=total_absent
    )

@admin_bp.route('/students/<int:id>/delete', methods=['POST'])
def student_delete(id):
    student = Student.query.get_or_404(id)
    name = student.full_name
    student_id = student.student_id

    db.session.delete(student)
    db.session.commit()

    SystemLog.log(
        action='STUDENT_DELETE',
        details=f'Deleted student {name} ({student_id}) and associated records',
        user_id=current_user.id,
        ip_address=get_client_ip()
    )

    flash(f'Student {name} deleted successfully.', 'info')
    return redirect(url_for('admin.students_list'))

@admin_bp.route('/students/qrcodes')
def batch_qrcodes():
    section = request.args.get('section', '')
    query = Student.query.filter_by(status='Active')
    if section:
        query = query.filter_by(section=section)
    students = query.order_by(Student.last_name.asc()).all()
    for s in students:
        qr_file = Path(current_app.config['QR_FOLDER']) / f"{s.qr_code_token}.png"
        if not qr_file.exists():
            s.qr_image_path = create_student_qr_image(s.qr_code_token)
    db.session.commit()
    sections = [s[0] for s in db.session.query(Student.section).distinct().all() if s[0]]

    return render_template('students/qrcodes.html', students=students, sections=sections, selected_section=section)

@admin_bp.route('/sessions', methods=['GET', 'POST'])
def sessions_manage():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        start_time_str = request.form.get('start_time', '').strip()
        late_threshold_str = request.form.get('late_threshold_time', '').strip()
        end_time_str = request.form.get('end_time', '').strip()

        if not name or not start_time_str or not late_threshold_str or not end_time_str:
            flash('All session schedule fields are required.', 'danger')
        else:
            try:
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                late_time = datetime.strptime(late_threshold_str, '%H:%M').time()
                end_time = datetime.strptime(end_time_str, '%H:%M').time()

                new_session = SessionSchedule(
                    name=name,
                    start_time=start_time,
                    late_threshold_time=late_time,
                    end_time=end_time,
                    is_active=True
                )
                db.session.add(new_session)
                db.session.commit()

                SystemLog.log(
                    action='SESSION_CREATE',
                    details=f'Created attendance session: {name}',
                    user_id=current_user.id,
                    ip_address=get_client_ip()
                )
                flash(f'Attendance session "{name}" added.', 'success')
            except ValueError:
                flash('Invalid time format. Please use HH:MM format.', 'danger')

        return redirect(url_for('admin.sessions_manage'))

    sessions = SessionSchedule.query.order_by(SessionSchedule.start_time.asc()).all()
    return render_template('admin/sessions.html', sessions=sessions)

@admin_bp.route('/logs')
def system_logs():
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '').strip()

    query = SystemLog.query
    if action:
        query = query.filter(SystemLog.action.ilike(f"%{action}%"))

    pagination = query.order_by(SystemLog.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    actions = [a[0] for a in db.session.query(SystemLog.action).distinct().all() if a[0]]

    return render_template('logs/index.html', pagination=pagination, logs=pagination.items, actions=actions, selected_action=action)

@admin_bp.route('/teachers')
def teachers_list():
    query = User.query.filter_by(role='Teacher')
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_fmt)) |
            (User.username.ilike(search_fmt)) |
            (User.email.ilike(search_fmt))
        )
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    teachers = query.order_by(User.full_name.asc()).all()
    return render_template('teachers/list.html', teachers=teachers, search=search, selected_status=status)

@admin_bp.route('/teachers/create', methods=['GET', 'POST'])
def teacher_create():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not full_name or not username or not email or not password:
            flash('All fields are required to register a teacher.', 'danger')
            return render_template('teachers/form.html', teacher=None)

        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" is already taken.', 'danger')
            return render_template('teachers/form.html', teacher=None)

        if User.query.filter_by(email=email).first():
            flash(f'Email address "{email}" is already registered.', 'danger')
            return render_template('teachers/form.html', teacher=None)

        new_teacher = User(
            username=username,
            full_name=full_name,
            email=email,
            role='Teacher',
            is_active=True
        )
        new_teacher.set_password(password)

        db.session.add(new_teacher)
        db.session.commit()

        SystemLog.log(
            action='TEACHER_CREATE',
            details=f'Registered teacher account for {new_teacher.full_name} ({new_teacher.username})',
            user_id=current_user.id,
            ip_address=get_client_ip()
        )

        flash(f'Professor {new_teacher.full_name} registered successfully!', 'success')
        return redirect(url_for('admin.teachers_list'))

    return render_template('teachers/form.html', teacher=None)

@admin_bp.route('/teachers/<int:id>/edit', methods=['GET', 'POST'])
def teacher_edit(id):
    teacher = User.query.filter_by(id=id, role='Teacher').first_or_404()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        is_active = request.form.get('is_active') == '1'

        if not full_name or not username or not email:
            flash('Full Name, Username, and Email are required.', 'danger')
            return render_template('teachers/form.html', teacher=teacher)

        existing_user = User.query.filter(User.username == username, User.id != id).first()
        if existing_user:
            flash(f'Username "{username}" is already taken.', 'danger')
            return render_template('teachers/form.html', teacher=teacher)

        existing_email = User.query.filter(User.email == email, User.id != id).first()
        if existing_email:
            flash(f'Email address "{email}" is already registered.', 'danger')
            return render_template('teachers/form.html', teacher=teacher)

        teacher.full_name = full_name
        teacher.username = username
        teacher.email = email
        teacher.is_active = is_active

        if password:
            teacher.set_password(password)

        db.session.commit()

        SystemLog.log(
            action='TEACHER_UPDATE',
            details=f'Updated teacher profile for {teacher.full_name} ({teacher.username})',
            user_id=current_user.id,
            ip_address=get_client_ip()
        )

        flash(f'Professor {teacher.full_name} updated successfully!', 'success')
        return redirect(url_for('admin.teachers_list'))

    return render_template('teachers/form.html', teacher=teacher)

@admin_bp.route('/teachers/<int:id>/toggle-status', methods=['POST'])
def teacher_toggle_status(id):
    teacher = User.query.filter_by(id=id, role='Teacher').first_or_404()
    teacher.is_active = not teacher.is_active
    db.session.commit()

    status_str = 'activated' if teacher.is_active else 'deactivated'
    SystemLog.log(
        action='TEACHER_STATUS_CHANGE',
        details=f'{status_str.capitalize()} account for {teacher.full_name} ({teacher.username})',
        user_id=current_user.id,
        ip_address=get_client_ip()
    )

    flash(f'Account for {teacher.full_name} has been {status_str}.', 'info')
    return redirect(url_for('admin.teachers_list'))

@admin_bp.route('/teachers/<int:id>/delete', methods=['POST'])
def teacher_delete(id):
    teacher = User.query.filter_by(id=id, role='Teacher').first_or_404()
    name = teacher.full_name
    db.session.delete(teacher)
    db.session.commit()

    SystemLog.log(
        action='TEACHER_DELETE',
        details=f'Deleted teacher account for {name}',
        user_id=current_user.id,
        ip_address=get_client_ip()
    )

    flash(f'Professor {name} has been deleted.', 'success')
    return redirect(url_for('admin.teachers_list'))

