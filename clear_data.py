import os
import glob
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from app import create_app
from app.models import db, Student, AttendanceRecord, SystemLog
from sqlalchemy import text

def clear_all_dummy_data():
    app = create_app()
    with app.app_context():
        print("🧹 Clearing all predefined dummy data...")

        # 1. Delete all Attendance Records
        deleted_attendances = AttendanceRecord.query.delete()
        print(f"  ✓ Deleted {deleted_attendances} attendance record(s)")

        # 2. Delete all Students
        deleted_students = Student.query.delete()
        print(f"  ✓ Deleted {deleted_students} student profile(s)")

        # 3. Delete all System Logs
        deleted_logs = SystemLog.query.delete()
        print(f"  ✓ Deleted {deleted_logs} system audit log(s)")

        db.session.commit()

        # 4. Reset AUTO_INCREMENT counters to 1
        try:
            db.session.execute(text("ALTER TABLE attendance_records AUTO_INCREMENT = 1;"))
            db.session.execute(text("ALTER TABLE students AUTO_INCREMENT = 1;"))
            db.session.execute(text("ALTER TABLE system_logs AUTO_INCREMENT = 1;"))
            db.session.commit()
            print("  ✓ Reset AUTO_INCREMENT counters to 1")
        except Exception as e:
            print(f"  Note on resetting auto-increment: {e}")

        # 5. Remove all generated QR Code image files in app/static/qrcodes
        qr_dir = Path(app.config['QR_FOLDER'])
        removed_files = 0
        if qr_dir.exists():
            for png_file in qr_dir.glob("*.png"):
                try:
                    png_file.unlink()
                    removed_files += 1
                except Exception as err:
                    print(f"  Could not delete {png_file.name}: {err}")
        print(f"  ✓ Removed {removed_files} QR code image file(s) from static/qrcodes/")

        print("\n✨ Database and files successfully cleaned!")
        print("👤 Login credentials preserved:")
        print("   - Admin: admin / admin123")
        print("   - Teacher: teacher / teacher123")

if __name__ == '__main__':
    clear_all_dummy_data()
