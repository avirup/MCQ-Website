# 📝 MCQ Test Platform

A web-based platform for creating, managing, and attempting multiple-choice questions (MCQs).  
Built with **Flask**, **SQLAlchemy**, **MariaDB**, **WTForms**, and styled with **Tailwind CSS**.  
💡 **Note:** This entire application was created collaboratively inside **ChatGPT-5** conversations — from design, models, and routes, to templates, styling, and advanced features.  

---

## 🚀 Features

- **Admin**
  - Manage subjects (create, edit, delete).
  - Manage questions with text and/or images.
  - Bulk upload questions via CSV + ZIP of images.
  - Bulk export questions + images (re-importable format).
  - Pagination in questions list for large datasets.
  - Inline subject filter & export dropdown with checkboxes.
  - Styled toast notifications (replaces default alerts).
  - Secure authentication for admin with CSRF protection.

- **Students**
  - Start tests in **display** or **interactive** mode.
  - Configure difficulty, number of questions, and timer mode.
  - Timer per-question or whole test.
  - Inline image display for questions/options.
  - Review answers and see detailed summaries.
  - Public sharing links for summaries and reviews.

- **General**
  - Responsive design with Tailwind CSS.
  - MathJax support for LaTeX rendering.
  - Cascading deletes (questions & subjects clean up images).
  - Custom 404 error page with cartoon & animation.

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask, SQLAlchemy, WTForms  
- **Frontend:** Tailwind CSS, Vanilla JS, MathJax  
- **Database:** **MariaDB** (tested with 10.x), but also works with MySQL  
- **Other:** Alembic migrations, Pillow for image validation  

---

## 📦 Setup Instructions

1. **Clone the repository**
   
   ```bash
   git clone <your-repo-url>
   cd MCQ-Website/src
   ````

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Linux/Mac
   .venv\Scripts\activate       # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install MariaDB and create a database**

   ```sql
   CREATE DATABASE mcq_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'mcq_user'@'localhost' IDENTIFIED BY 'strongpassword';
   GRANT ALL PRIVILEGES ON mcq_platform.* TO 'mcq_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

5. **Set environment variables (example)**

   ```bash
   export FLASK_APP=app.py
   export FLASK_ENV=development
   export SECRET_KEY=your-secret-key
   export UPLOAD_DIR=uploads
   export DATABASE_URL="mysql+pymysql://mcq_user:strongpassword@localhost/mcq_platform"
   ```

6. **Run database migrations**

   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

7. **Run the server**

   ```bash
   flask run
   ```

8. Visit: [http://localhost:5000](http://localhost:5000)

9. **Create Admin Password**

   ```bash
   flask run
   ```

---

## 📂 Project Structure

```
src/
├── app.py                # Flask app entry point
├── extensions.py         # DB + login manager setup
├── models.py             # SQLAlchemy models
├── routes/               # Blueprints (auth, admin, student, uploads)
├── templates/            # Jinja2 templates (admin, student, shared)
├── static/               # JS, CSS, images
├── migrations/           # Alembic migration scripts
└── uploads/              # Uploaded question/option images (gitignored)
```

---

## 🧹 Housekeeping

* `.gitignore` excludes:

  * Python cache & virtual env (`__pycache__`, `.venv/`)
  * Database dumps/backups (`*.sql`, `*.db`)
  * Uploads folder (`/uploads`)
  * Local editor configs (`.vscode/`, `.idea/`)
  * Alembic migration cache

* **Image cleanup**

  * When deleting a **question**, its images are deleted.
  * When deleting a **subject**, its folder and all question images are deleted.

---

## ✅ To Do / Improvements

* Add user accounts (students & teachers).
* Rich text editor for question input.
* Better reporting & analytics for test results.
* API endpoints for mobile integration.

---

## 👨‍💻 Development Notes

* Routes decorated with `@admin_required` ensure only admins access them.
* Flash messages and errors are displayed as styled **toasts** instead of raw alerts.
* Bulk export format matches bulk upload format → exported zip can be directly re-imported.

---

