# 📝 MCQ Test Platform

A web-based platform for creating, managing, and attempting multiple-choice questions (MCQs).  
Built with **Flask**, **SQLAlchemy**, **MariaDB**, **WTForms**, and styled with **Tailwind CSS**.  
💡 **Note:** This entire application was created collaboratively inside **ChatGPT-5** conversations — from design, models, and routes, to templates, styling, and advanced features.  

---

## 🚀 Features
...


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
