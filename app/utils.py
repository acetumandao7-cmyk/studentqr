import os
import uuid
from functools import wraps
from pathlib import Path
import qrcode
from PIL import Image
from flask import request, abort, current_app
from flask_login import current_user
from app.models import db, AttendanceRecord

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_verification_base_url():
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if render_url:
        return render_url.rstrip('/')
    base_url = os.environ.get('BASE_URL')
    if base_url:
        return base_url.rstrip('/')
    try:
        from flask import has_request_context, request
        if has_request_context():
            proto = request.headers.get('X-Forwarded-Proto', request.scheme)
            host = request.headers.get('X-Forwarded-Host', request.host)
            return f"{proto}://{host}".rstrip('/')
    except Exception:
        pass
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return f"http://{ip}:5000"
    except Exception:
        return "http://127.0.0.1:5000"

def generate_qr_token(student_id: str) -> str:
    unique_suffix = uuid.uuid4().hex[:12].upper()
    sanitized_id = student_id.replace(" ", "-").upper()
    return f"SQRS-{sanitized_id}-{unique_suffix}"

def create_student_qr_image(qr_token: str, student_info: dict = None) -> str:
    qr_dir = Path(current_app.config['QR_FOLDER'])
    qr_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{qr_token}.png"
    file_path = qr_dir / file_name

    base_url = get_verification_base_url()
    qr_payload = f"{base_url}/verify/{qr_token}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert('RGB')
    img.save(str(file_path))

    return f"/static/qrcodes/{file_name}"

def check_duplicate_attendance(student_id: int, session_id: int, target_date):
    record = AttendanceRecord.query.filter_by(
        student_id=student_id,
        session_id=session_id,
        date=target_date
    ).first()
    return (record is not None, record)
