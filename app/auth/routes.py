from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, SystemLog
from app.utils import get_client_ip

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('attendance.teacher_dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not identifier or not password:
            flash('Please enter both username/email and password.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()

            SystemLog.log(
                action='USER_LOGIN',
                details=f'User {user.username} ({user.role}) logged in successfully.',
                user_id=user.id,
                ip_address=get_client_ip()
            )

            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('attendance.teacher_dashboard'))

        flash('Invalid username/email or password.', 'danger')
        SystemLog.log(
            action='LOGIN_FAILED',
            details=f'Failed login attempt for identifier: {identifier}',
            ip_address=get_client_ip()
        )

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    user_id = current_user.id
    logout_user()
    SystemLog.log(
        action='USER_LOGOUT',
        details=f'User {username} logged out.',
        user_id=user_id,
        ip_address=get_client_ip()
    )
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('auth.login'))
