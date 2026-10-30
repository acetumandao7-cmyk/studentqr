import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-studentqr-key-2026-prod-grade')
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{BASE_DIR / 'instance' / 'student_attendance.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    QR_FOLDER = BASE_DIR / 'app' / 'static' / 'qrcodes'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024