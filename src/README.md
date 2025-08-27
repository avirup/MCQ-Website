# MCQ Test Platform (Starter Kit)

This is a starter scaffold for a Flask + MariaDB MCQ Test Platform.

## 1) Setup (Windows PowerShell)

```powershell
cd mcq_platform
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Configure Environment

Edit `.env` with your DB connection and secrets.

Optional: Create `.flaskenv` for dev convenience:

```ini
FLASK_APP=manage.py
FLASK_ENV=development
```

## 3) Initialize Database (after you add models later)
```powershell
flask db init
flask db migrate -m "init"
flask db upgrade
```

## 4) Run the App
```powershell
flask --app manage.py run
```

## 5) Sample Data
The `sample_data/` folder includes small CSVs you can use later for bulk upload features.

## 6) Structure
- `app.py` – app factory, registers blueprints
- `routes/` – blueprints for auth, admin, student, api
- `services/` – business logic (to implement)
- `templates/` – Jinja templates
- `static/` – CSS/JS placeholders
- `uploads/` – image uploads
- `migrations/` – alembic (created by Flask-Migrate)
- `tests/` – pytest tests (basic example)
