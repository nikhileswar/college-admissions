# CollegeMatch — Django Stable Matching System
### JEE Advanced 2025 · Gale-Shapley Algorithm

A full-stack Django web application for stable seat allocation across all 23 IITs,
using the student-proposing Gale-Shapley algorithm.

---

## 🚀 Quick Start

### 1. Install Python (3.10+) and pip

### 2. Extract and enter the project folder
```bash
cd collegmatch
```

### 3. (Optional) Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 4. Run the setup script
```bash
chmod +x setup.sh
./setup.sh
```
This installs Django, runs migrations, and creates the admin user.

Or manually:
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py create_admin
```

### 5. Start the development server
```bash
python manage.py runserver
```

### 6. Open the app
Visit: **http://127.0.0.1:8000**

---

## 🔑 Login Credentials

| Role   | Username | Password   |
|--------|----------|------------|
| Admin  | admin    | admin123   |
| Student (demo) | e.g. `air001_rajit` | jee2025 |

> After logging in as admin, go to **Setup → Load JEE 2025 Demo**
> to populate 200 students across all 23 IITs.

---

## 📁 Project Structure

```
collegmatch/
├── manage.py
├── requirements.txt
├── setup.sh
├── collegmatch/               # Django project settings
│   ├── settings.py
│   └── urls.py
└── matching/                  # Main Django app
    ├── models.py              # Branch, StudentProfile, Preference, MatchingResult, Allotment
    ├── views.py               # All views (admin + student portals)
    ├── forms.py               # Signup, Login, Branch, Student forms
    ├── algorithm.py           # Gale-Shapley implementation
    ├── urls.py                # URL routing
    ├── admin.py               # Django admin registration
    ├── templates/matching/
    │   ├── base.html          # Shared layout + nav
    │   ├── login.html         # Login + signup page
    │   ├── admin_setup.html   # Admin: manage branches & students
    │   ├── admin_preferences.html  # Admin: view all preferences
    │   ├── admin_student_detail.html
    │   ├── admin_results.html # Admin: run & view matching
    │   ├── student_preferences.html  # Student: drag-to-rank prefs
    │   └── student_allotment.html    # Student: view allotment
    ├── static/matching/
    │   ├── css/main.css
    │   └── js/main.js
    └── management/commands/
        └── create_admin.py    # Custom management command
```

---

## ✨ Features

### Login Page
- **Student Login** — username + password
- **Student Sign Up** — name, AIR rank, username, password
- **Admin Login** — separate tab for staff access

### Admin Portal
- **Setup** — Add/delete colleges & branches with seat counts; Add/delete students manually; Load 200-student JEE 2025 demo data
- **All Preferences** — Searchable table of every student's submission status and top 5 choices; view full preference list per student
- **Results** — Run Gale-Shapley matching with one click; see all allotments by branch with preference ranks; unmatched students listed separately

### Student Portal
- **My Preferences** — Drag-and-drop reordering of all college-branch pairs; save via AJAX without page reload
- **My Allotment** — View personal seat allotment with preference rank; pending banner if matching hasn't run yet

---

## ⚙ Algorithm

The **student-proposing Gale-Shapley** algorithm is implemented in `algorithm.py`:

1. All students start as free (unmatched)
2. Each free student proposes to their next preferred branch
3. The branch tentatively accepts if it has a free seat, or displaces its weakest current holder if the new proposer has a better AIR rank (lower = better)
4. Displaced students re-enter the free pool
5. Repeat until no free students remain or all preferences exhausted

**Result**: Student-optimal stable matching — every student gets the best seat they can possibly get in any stable matching.

---

## 🛠 Production Notes

For production deployment:
1. Change `SECRET_KEY` in `settings.py`
2. Set `DEBUG = False`
3. Configure `ALLOWED_HOSTS`
4. Use PostgreSQL instead of SQLite
5. Add `django.contrib.staticfiles` collector (`collectstatic`)
6. Deploy with gunicorn + nginx
