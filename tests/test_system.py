import unittest
from datetime import date, datetime, time
from app import create_app
from app.models import db, User, Student, SessionSchedule, AttendanceRecord
from app.utils import check_duplicate_attendance

class AttendanceSystemTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_user_authentication(self):
        admin = User.query.filter_by(username='admin').first()
        self.assertIsNotNone(admin)
        self.assertTrue(admin.check_password('admin123'))
        self.assertTrue(admin.is_admin)

        teacher = User.query.filter_by(username='teacher').first()
        self.assertIsNotNone(teacher)
        self.assertTrue(teacher.check_password('teacher123'))
        self.assertFalse(teacher.is_admin)

    def test_duplicate_attendance_logic(self):
        student = Student.query.first()
        session = SessionSchedule.query.first()
        temp_student = False
        if not student:
            student = Student(
                student_id='TEST-TMP-01',
                first_name='Test',
                last_name='Student',
                gender='Male',
                course_grade='BSIT',
                section='1A',
                qr_code_token='TEST-TOKEN-01'
            )
            db.session.add(student)
            db.session.commit()
            temp_student = True
        self.assertIsNotNone(student)
        self.assertIsNotNone(session)

        test_date = date(2026, 12, 1)
        AttendanceRecord.query.filter_by(student_id=student.id, session_id=session.id, date=test_date).delete()
        db.session.commit()

        is_dup, _ = check_duplicate_attendance(student.id, session.id, test_date)
        self.assertFalse(is_dup)

        rec = AttendanceRecord(
            student_id=student.id,
            session_id=session.id,
            date=test_date,
            timestamp=datetime.now(),
            status='Present',
            scan_method='QR_SCAN'
        )
        db.session.add(rec)
        db.session.commit()

        is_dup_now, existing = check_duplicate_attendance(student.id, session.id, test_date)
        self.assertTrue(is_dup_now)
        self.assertEqual(existing.status, 'Present')

        db.session.delete(rec)
        if temp_student:
            db.session.delete(student)
        db.session.commit()

    def test_session_status_classification(self):
        session = SessionSchedule(
            name='Test Class',
            start_time=time(8, 0),
            late_threshold_time=time(8, 15),
            end_time=time(10, 0)
        )
        self.assertEqual(session.determine_status(time(8, 5)), 'Present')
        self.assertEqual(session.determine_status(time(8, 15)), 'Present')
        self.assertEqual(session.determine_status(time(8, 16)), 'Late')
        self.assertEqual(session.determine_status(time(9, 0)), 'Late')

if __name__ == '__main__':
    unittest.main()
