# Smart Student Attendance and Monitoring System using QR Code

A modern, responsive, and secure web application designed to automate and monitor student attendance in real time using unique QR code identification tokens. Built with **Python (Flask)**, **MySQL (XAMPP compatible)**, and modern responsive frontend standards.

---

## 🚀 Key Features

* **Role-Based Access Control (RBAC)**: Secure authentication with Werkzeug password hashing for Administrators and Teachers.
* **Instant QR Code Generation**: Unique cryptographic QR code tokens generated for every student with downloadable & printable ID badges.
* **Camera-Enabled Web Scanner**: Fast browser-based QR scanner supporting desktop webcams and mobile cameras, with instant audio-visual feedback.
* **Duplicate Scan Prevention**: Database-level `UNIQUE KEY (student_id, session_id, date)` constraint and application-level verification preventing double attendance entries for the same session.
* **Automated Status Processing**: Automatically flags scans as **Present** or **Late** based on configurable class schedules and threshold times.
* **Student Directory CRUD**: Comprehensive student profile management with search, course/section filtering, and QR badge regeneration.
* **Teacher Monitoring Dashboard**: Real-time attendance stream and live turnout statistics.
* **Automated Reporting & Export**: Daily, weekly, and monthly attendance auditing with single-click CSV export and print-ready summary views.
* **System Audit Trail**: Complete activity logging capturing logins, attendance scans, IP addresses, and database changes.

---

## 🛠️ Tech Stack & Requirements

* **Backend**: Python 3.10+ (Flask, Flask-SQLAlchemy, Flask-Login, PyMySQL, Cryptography, Pillow, QRCode)
* **Frontend**: HTML5, Vanilla CSS3 (Custom Design System with Glassmorphism), Modern JavaScript (Fetch API, Web Audio API chime synthesis, `html5-qrcode`)
* **Database**: MySQL 5.7+ / MariaDB 10.4+ (Default port: `3306`, user: `root`)
* **Environment**: XAMPP and Google Antigravity

---

## 📁 Project File Structure

```text
studentqr/
├── app/
│   ├── __init__.py           # Flask application factory & blueprint registry
│   ├── config.py             # MySQL database URI & application settings
│   ├── models.py             # SQLAlchemy models (User, Student, Session, Attendance, Log)
│   ├── utils.py              # QR generation, duplicate check, and RBAC helpers
│   ├── auth/
│   │   └── routes.py         # Login, logout, and credential validation
│   ├── admin/
│   │   └── routes.py         # Student CRUD, batch QR generation, session configs, logs
│   ├── attendance/
│   │   └── routes.py         # Camera scanner view, sub-second scan API, teacher monitor
│   ├── reports/
│   │   └── routes.py         # Daily/Weekly/Monthly attendance reports & CSV exporter
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css    # Premium CSS design system, responsive layout, ID cards
│   │   ├── js/
│   │   │   ├── main.js       # Live clock, Web Audio feedback synthesizer, mobile nav
│   │   │   └── scanner.js    # Camera scanner logic, live result card, duplicate warnings
│   │   └── qrcodes/          # Generated student QR PNG images
│   └── templates/
│       ├── base.html         # Sidebar, top navigation, flash alerts
│       ├── auth/login.html   # Modern sign-in view
│       ├── dashboard/
│       │   ├── admin.html    # Administrator overview & analytics
│       │   └── teacher.html  # Live monitoring dashboard for teachers
│       ├── students/
│       │   ├── list.html     # Student directory with search & filters
│       │   ├── form.html     # Registration & profile update form
│       │   ├── profile.html  # Printable student ID card with QR & history
│       │   └── qrcodes.html  # Batch printable sheet of student ID badges
│       ├── attendance/
│       │   └── scanner.html  # Camera scanner interface with audio feedback
│       ├── reports/
│       │   └── index.html    # Daily/Weekly/Monthly reports with CSV export
│       ├── admin/
│       │   └── sessions.html # Session schedule & late cutoff configuration
│       └── logs/
│           └── index.html    # Security audit trail
├── schema.sql                # Complete MySQL DDL schema script
├── seed.py                   # Automated database seeder with sample students & QR codes
├── run.py                    # Application entrypoint
├── requirements.txt          # Python package dependencies
└── tests/
    └── test_system.py        # Automated test suite
```

---

## ⚙️ Quick Start Guide

### 1. Start XAMPP MySQL
Ensure the **MySQL module** is running in your XAMPP Control Panel on default port `3306`.

### 2. Create the Database Schema
The database and tables can be created via the provided SQL script:
```powershell
Get-Content schema.sql | & "C:\xampp\mysql\bin\mysql.exe" -u root
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Seed Default Users & Sample Students
Run the seeder script to populate default admin/teacher accounts, class schedules, and sample student records with real QR codes:
```powershell
python seed.py
```

### 5. Launch the Application
```powershell
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🔑 Default Credentials

| Role | Username | Password | Email | Access |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | `admin@school.edu` | Full control: Student CRUD, batch QR badges, sessions, audit logs, reports |
| **Teacher** | `teacher` | `teacher123` | `eleanor.vance@school.edu` | Camera QR scanner, real-time attendance monitor, section reports |

---

## 🧪 Running Automated Tests
```powershell
python -m unittest tests/test_system.py
```
