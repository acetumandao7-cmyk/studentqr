import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-studentqr-key-2026-prod-grade')

    INSTANCE_DIR = BASE_DIR / 'instance'
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{INSTANCE_DIR / 'student_attendance.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    QR_FOLDER = BASE_DIR / 'app' / 'static' / 'qrcodes'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024