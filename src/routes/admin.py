# routes/admin.py
from __future__ import annotations

from pathlib import Path
import os, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, make_response
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from wtforms import StringField, TextAreaField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Length, AnyOf, Optional as Opt
from flask_wtf import FlaskForm
from PIL import Image

from routes.auth import admin_required
from extensions import db
from models import Subject, Question


import csv
import io
import zipfile
import tempfile
from typing import Dict, Tuple, Optional




admin_bp = Blueprint("admin", __name__)

# -----------------------
# Helpers / constants
# -----------------------

ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp"}  # (avoid svg for XSS risk)
MAX_IMAGE_BYTES = 1 * 1024 * 1024  # 1MB

def _allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXT

def _save_image(file_storage, subject_id: int) -> str:
    """
    Validate and save an uploaded image under UPLOAD_DIR/<subject_id>/.
    Returns relative path to store in DB. Raises ValueError on invalid files.
    """
    if not file_storage or file_storage.filename == "":
        return None

    filename = secure_filename(file_storage.filename)
    if not _allowed_file(filename):
        raise ValueError("Unsupported file type. Allowed: " + ", ".join(sorted(ALLOWED_EXT)))

    # Enforce size limit
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_IMAGE_BYTES:
        raise ValueError(f"File too large (>{MAX_IMAGE_BYTES} bytes).")

    # Basic image sanity check (Pillow)
    try:
        img = Image.open(file_storage.stream)
        img.verify()  # verifies but doesn't decode; cheap
    except Exception:
        raise ValueError("Uploaded file is not a valid image.")

    # Reset stream for saving
    file_storage.stream.seek(0)

    # Build unique filename
    ext = filename.rsplit(".", 1)[-1].lower()
    unique = f"{uuid.uuid4().hex}.{ext}"

    base_dir = Path(current_app.config["UPLOAD_DIR"]).resolve()
    target_dir = base_dir / str(subject_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    full_path = target_dir / unique
    file_storage.save(full_path)

    # Return path relative to UPLOAD_DIR root for easier moves later
    rel_path = str(Path(str(subject_id)) / unique)
    return rel_path

# -----------------------
# WTForms
# -----------------------

class QuestionForm(FlaskForm):
    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    question_text = TextAreaField("Question (LaTeX allowed)", validators=[DataRequired(), Length(max=2000)])
    # Optional question image
    question_image = FileField("Question image (optional)", validators=[Opt()])

    option_a = TextAreaField("Option A", validators=[DataRequired()])
    option_a_image = FileField("Option A image (optional)", validators=[Opt()])

    option_b = TextAreaField("Option B", validators=[DataRequired()])
    option_b_image = FileField("Option B image (optional)", validators=[Opt()])

    option_c = TextAreaField("Option C", validators=[DataRequired()])
    option_c_image = FileField("Option C image (optional)", validators=[Opt()])

    option_d = TextAreaField("Option D", validators=[DataRequired()])
    option_d_image = FileField("Option D image (optional)", validators=[Opt()])

    correct_option = SelectField(
        "Correct Option",
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        validators=[DataRequired(), AnyOf(values=["A", "B", "C", "D"])],
    )

    submit = SubmitField("Save")


@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")

# ---------- Subjects CRUD ----------

@admin_bp.route("/subjects", methods=["GET"])
@admin_required
def subjects():
    """List subjects + create form."""
    subjects = Subject.query.order_by(Subject.name.asc()).all()
    return render_template("admin/subjects.html", subjects=subjects, edit_mode=False, form_data={})

@admin_bp.route("/subjects", methods=["POST"])
@admin_required
def subjects_create():
    """Create a new subject with server-side validation."""
    name = (request.form.get("name") or "").strip()

    # Validation
    errors = {}
    if not name:
        errors["name"] = "Subject name is required."
    elif len(name) > 100:
        errors["name"] = "Subject name must be 100 characters or fewer."
    else:
        # Case-insensitive uniqueness check
        exists = (
            db.session.query(Subject.id)
            .filter(func.lower(Subject.name) == name.lower())
            .first()
        )
        if exists:
            errors["name"] = "A subject with this name already exists."

    if errors:
        subjects = Subject.query.order_by(Subject.name.asc()).all()
        flash("Please fix the errors below.", "error")
        return render_template(
            "admin/subjects.html",
            subjects=subjects,
            edit_mode=False,
            form_data={"name": name},
            errors=errors,
        ), 400

    try:
        db.session.add(Subject(name=name))
        db.session.commit()
        flash("Subject created.", "success")
        return redirect(url_for("admin.subjects"))
    except IntegrityError:
        db.session.rollback()
        flash("Could not create subject due to a database error.", "error")
        return redirect(url_for("admin.subjects"))

@admin_bp.route("/subjects/<int:subject_id>/edit", methods=["GET"])
@admin_required
def subjects_edit(subject_id: int):
    """Render edit form (using same template)."""
    subj = Subject.query.get_or_404(subject_id)
    subjects = Subject.query.order_by(Subject.name.asc()).all()
    return render_template(
        "admin/subjects.html",
        subjects=subjects,
        edit_mode=True,
        editing=subj,
        form_data={"name": subj.name},
    )

@admin_bp.route("/subjects/<int:subject_id>/edit", methods=["POST"])
@admin_required
def subjects_update(subject_id: int):
    """Update an existing subject with validation."""
    subj = Subject.query.get_or_404(subject_id)
    name = (request.form.get("name") or "").strip()

    errors = {}
    if not name:
        errors["name"] = "Subject name is required."
    elif len(name) > 100:
        errors["name"] = "Subject name must be 100 characters or fewer."
    else:
        # Uniqueness excluding current subject
        exists = (
            db.session.query(Subject.id)
            .filter(func.lower(Subject.name) == name.lower(), Subject.id != subj.id)
            .first()
        )
        if exists:
            errors["name"] = "Another subject with this name already exists."

    if errors:
        subjects = Subject.query.order_by(Subject.name.asc()).all()
        flash("Please fix the errors below.", "error")
        return render_template(
            "admin/subjects.html",
            subjects=subjects,
            edit_mode=True,
            editing=subj,
            form_data={"name": name},
            errors=errors,
        ), 400

    try:
        subj.name = name
        db.session.commit()
        flash("Subject updated.", "success")
        return redirect(url_for("admin.subjects"))
    except IntegrityError:
        db.session.rollback()
        flash("Could not update subject due to a database error.", "error")
        return redirect(url_for("admin.subjects"))

@admin_bp.route("/subjects/<int:subject_id>/delete", methods=["POST"])
@admin_required
def subjects_delete(subject_id: int):
    """Delete a subject. (Questions will cascade if your model is set to do so.)"""
    subj = Subject.query.get_or_404(subject_id)
    try:
        db.session.delete(subj)
        db.session.commit()
        flash("Subject deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Could not delete subject due to a database error.", "error")
    return redirect(url_for("admin.subjects"))

# -----------------------
# Questions: List / Filter
# -----------------------

@admin_bp.route("/questions", methods=["GET"])
@admin_required
def questions():
    subject_id = request.args.get("subject_id", type=int)
    q = Question.query
    if subject_id:
        q = q.filter(Question.subject_id == subject_id)

    questions = q.order_by(Question.id.desc()).limit(200).all()  # cap to 200 for now
    subjects = Subject.query.order_by(Subject.name.asc()).all()
    return render_template("admin/questions_list.html", questions=questions, subjects=subjects, selected_subject_id=subject_id)

# -----------------------
# Questions: Create
# -----------------------

@admin_bp.route("/questions/new", methods=["GET", "POST"])
@admin_required
def questions_new():
    form = QuestionForm()
    # Populate subject choices
    form.subject_id.choices = [(s.id, s.name) for s in Subject.query.order_by(Subject.name.asc()).all()]

    if form.validate_on_submit():
        try:
            # Save images if provided
            q_img = _save_image(request.files.get("question_image"), form.subject_id.data)
            oa_img = _save_image(request.files.get("option_a_image"), form.subject_id.data)
            ob_img = _save_image(request.files.get("option_b_image"), form.subject_id.data)
            oc_img = _save_image(request.files.get("option_c_image"), form.subject_id.data)
            od_img = _save_image(request.files.get("option_d_image"), form.subject_id.data)

            q = Question(
                subject_id=form.subject_id.data,
                question_text=form.question_text.data.strip(),
                question_image=q_img,
                option_a=form.option_a.data.strip(),
                option_a_image=oa_img,
                option_b=form.option_b.data.strip(),
                option_b_image=ob_img,
                option_c=form.option_c.data.strip(),
                option_c_image=oc_img,
                option_d=form.option_d.data.strip(),
                option_d_image=od_img,
                correct_option=form.correct_option.data,
            )
            db.session.add(q)
            db.session.commit()
            flash("Question created.", "success")
            return redirect(url_for("admin.questions", subject_id=form.subject_id.data))
        except ValueError as e:
            flash(str(e), "error")
        except IntegrityError:
            db.session.rollback()
            flash("Database error while creating question.", "error")

    return render_template("admin/question_form.html", form=form, edit_mode=False)

# -----------------------
# Questions: Edit
# -----------------------

@admin_bp.route("/questions/<int:qid>/edit", methods=["GET", "POST"])
@admin_required
def questions_edit(qid: int):
    q = Question.query.get_or_404(qid)

    form = QuestionForm(obj=q)
    form.subject_id.choices = [(s.id, s.name) for s in Subject.query.order_by(Subject.name.asc()).all()]

    if form.validate_on_submit():
        try:
            q.subject_id = form.subject_id.data
            q.question_text = form.question_text.data.strip()
            q.option_a = form.option_a.data.strip()
            q.option_b = form.option_b.data.strip()
            q.option_c = form.option_c.data.strip()
            q.option_d = form.option_d.data.strip()
            q.correct_option = form.correct_option.data

            # Replace images only if a new file is provided
            new_qimg = request.files.get("question_image")
            if new_qimg and new_qimg.filename:
                q.question_image = _save_image(new_qimg, q.subject_id)

            new_oa = request.files.get("option_a_image")
            if new_oa and new_oa.filename:
                q.option_a_image = _save_image(new_oa, q.subject_id)

            new_ob = request.files.get("option_b_image")
            if new_ob and new_ob.filename:
                q.option_b_image = _save_image(new_ob, q.subject_id)

            new_oc = request.files.get("option_c_image")
            if new_oc and new_oc.filename:
                q.option_c_image = _save_image(new_oc, q.subject_id)

            new_od = request.files.get("option_d_image")
            if new_od and new_od.filename:
                q.option_d_image = _save_image(new_od, q.subject_id)

            db.session.commit()
            flash("Question updated.", "success")
            return redirect(url_for("admin.questions", subject_id=q.subject_id))
        except ValueError as e:
            flash(str(e), "error")
        except IntegrityError:
            db.session.rollback()
            flash("Database error while updating question.", "error")

    return render_template("admin/question_form.html", form=form, edit_mode=True, q=q)

# -----------------------
# Questions: Delete
# -----------------------

@admin_bp.route("/questions/<int:qid>/delete", methods=["POST"])
@admin_required
def questions_delete(qid: int):
    q = Question.query.get_or_404(qid)
    try:
        db.session.delete(q)
        db.session.commit()
        flash("Question deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Could not delete question due to a database error.", "error")
    return redirect(url_for("admin.questions"))


# ---------- Bulk Upload Form ----------

class BulkUploadForm(FlaskForm):
    csv_file = FileField("Questions CSV", validators=[DataRequired()])
    images_zip = FileField("Images ZIP (optional)")
    submit = SubmitField("Upload")

# ---------- Image helpers for ZIP members ----------

def _save_image_from_bytes(data: bytes, original_name: str, subject_id: int) -> str:
    """
    Validate and save an uploaded image given as raw bytes.
    Returns a relative path (e.g., "5/uuid.png") to store in the DB.
    """
    # Extension check from original_name
    if not _allowed_file(original_name):
        raise ValueError("Unsupported file type. Allowed: " + ", ".join(sorted(ALLOWED_EXT)))

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"File too large (>{MAX_IMAGE_BYTES} bytes).")

    # Validate image via Pillow
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise ValueError("Uploaded file is not a valid image.")

    # Build unique filename
    ext = original_name.rsplit(".", 1)[-1].lower()
    unique = f"{uuid.uuid4().hex}.{ext}"

    base_dir = Path(current_app.config["UPLOAD_DIR"]).resolve()
    target_dir = base_dir / str(subject_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    full_path = target_dir / unique
    with open(full_path, "wb") as f:
        f.write(data)

    rel_path = str(Path(str(subject_id)) / unique)
    return rel_path

def _zip_members_map(zip_fs: Optional[FileStorage]) -> Dict[str, str]:
    """
    Build a case-insensitive map of filename -> canonical zip member name.
    We strip directories and only keep the final basename.
    Returns dict with keys lowercased basenames.
    """
    mapping: Dict[str, str] = {}
    if not zip_fs or not zip_fs.filename:
        return mapping

    zip_bytes = zip_fs.read()
    # reset stream for safety if needed later
    zip_fs.stream = io.BytesIO(zip_bytes)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            base = Path(name).name  # strip directories
            mapping[base.lower()] = name
    return mapping

def _read_zip_member(zip_fs: FileStorage, member_name: str) -> bytes:
    """
    Read raw bytes of a member from a zip FileStorage (member_name must be exact in the archive).
    """
    zip_fs.stream.seek(0)
    with zipfile.ZipFile(zip_fs.stream) as zf:
        with zf.open(member_name) as f:
            return f.read()

# ---------- CSV Parsing & Row Handling ----------

REQUIRED_COLUMNS = [
    "subject", "question_text", "option_a", "option_b", "option_c", "option_d", "correct_option"
]
OPTIONAL_IMAGE_COLUMNS = [
    "question_image",
    "option_a_image", "option_b_image", "option_c_image", "option_d_image",
]

def _normalize_header(h: str) -> str:
    return h.strip().lower()

def _get_subject_id_by_name(name: str) -> Optional[int]:
    if not name:
        return None
    subj = Subject.query.filter(func.lower(Subject.name) == name.lower()).first()
    return subj.id if subj else None

def _validate_row_dict(row: dict) -> Tuple[bool, str]:
    # required fields present?
    for col in REQUIRED_COLUMNS:
        if _normalize_header(col) not in row or not (row.get(col) or "").strip():
            return False, f"Missing required field: {col}"

    # correct_option valid?
    co = (row.get("correct_option") or "").strip().upper()
    if co not in {"A", "B", "C", "D"}:
        return False, "correct_option must be one of A, B, C, D"

    # question_text length
    if len((row.get("question_text") or "")) > 2000:
        return False, "question_text exceeds 2000 characters"

    return True, ""

# ---------- Route: Bulk Upload ----------

@admin_bp.route("/bulk-upload", methods=["GET", "POST"])
@admin_required
def bulk_upload():
    form = BulkUploadForm()
    summary = None
    errors = []
    successes = 0

    if form.validate_on_submit():
        csv_fs: FileStorage = form.csv_file.data
        zip_fs: Optional[FileStorage] = form.images_zip.data if form.images_zip.data and form.images_zip.data.filename else None

        # Build quick lookup map for images inside the ZIP, if provided
        zip_map = _zip_members_map(zip_fs) if zip_fs else {}

        # Read CSV rows
        try:
            csv_bytes = csv_fs.read()
            csv_text = csv_bytes.decode("utf-8-sig")  # handle BOM if present
            reader = csv.DictReader(io.StringIO(csv_text))
            headers = [ _normalize_header(h) for h in (reader.fieldnames or []) ]

            # Basic header validation
            for col in REQUIRED_COLUMNS:
                if col not in headers:
                    errors.append(f"CSV missing required column: {col}")
            for opt in OPTIONAL_IMAGE_COLUMNS:
                # optional, do not error if missing
                pass
            if errors:
                return render_template("admin/bulk_upload.html", form=form, summary=None, errors=errors), 400

            # Process each row independently
            row_num = 1  # header = row 1
            for row in reader:
                row_num += 1

                # Make uniform lower keys
                normalized = { _normalize_header(k): (v or "").strip() for k, v in row.items() }

                ok, msg = _validate_row_dict(normalized)
                if not ok:
                    errors.append(f"Row {row_num}: {msg}")
                    continue

                subject_name = normalized["subject"]
                subject_id = _get_subject_id_by_name(subject_name)
                if not subject_id:
                    errors.append(f"Row {row_num}: Subject '{subject_name}' not found. Create it first.")
                    continue

                # Resolve images (if any) from ZIP
                def resolve_img(field: str) -> Optional[str]:
                    fn = normalized.get(field) or ""
                    if not fn:
                        return None
                    if not zip_fs:
                        errors.append(f"Row {row_num}: '{field}' refers to '{fn}', but no ZIP was uploaded.")
                        return None
                    key = Path(fn).name.lower()
                    member = zip_map.get(key)
                    if not member:
                        errors.append(f"Row {row_num}: Image '{fn}' not found in ZIP.")
                        return None
                    try:
                        data = _read_zip_member(zip_fs, member)
                        return _save_image_from_bytes(data, original_name=fn, subject_id=subject_id)
                    except ValueError as e:
                        errors.append(f"Row {row_num}: {field} invalid - {e}")
                        return None
                    except Exception:
                        errors.append(f"Row {row_num}: Failed to read image '{fn}' from ZIP.")
                        return None

                q_img = resolve_img("question_image")
                oa_img = resolve_img("option_a_image")
                ob_img = resolve_img("option_b_image")
                oc_img = resolve_img("option_c_image")
                od_img = resolve_img("option_d_image")

                try:
                    q = Question(
                        subject_id=subject_id,
                        question_text=normalized["question_text"],
                        question_image=q_img,
                        option_a=normalized["option_a"],
                        option_a_image=oa_img,
                        option_b=normalized["option_b"],
                        option_b_image=ob_img,
                        option_c=normalized["option_c"],
                        option_c_image=oc_img,
                        option_d=normalized["option_d"],
                        option_d_image=od_img,
                        correct_option=normalized["correct_option"].upper(),
                    )
                    db.session.add(q)
                    db.session.commit()
                    successes += 1
                except IntegrityError:
                    db.session.rollback()
                    errors.append(f"Row {row_num}: Database error while inserting.")
                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Row {row_num}: Unexpected error: {e}")

        except UnicodeDecodeError:
            errors.append("CSV is not UTF-8 encoded. Save as UTF-8 and try again.")
        except Exception as e:
            errors.append(f"Failed to read CSV: {e}")

        summary = {
            "created": successes,
            "failed": len(errors),
        }

    return render_template("admin/bulk_upload.html", form=form, summary=summary, errors=errors)


# Create a downloadable template for question upload format 
@admin_bp.route("/download-template", methods=["GET"])
@admin_required
def download_template():
    """
    Serve a CSV template for bulk question upload.
    Append ?sample=1 to include one example row.
    """
    headers = [
        "subject",
        "question_text",
        "question_image",
        "option_a",
        "option_a_image",
        "option_b",
        "option_b_image",
        "option_c",
        "option_c_image",
        "option_d",
        "option_d_image",
        "correct_option",
    ]

    include_sample = request.args.get("sample") in ("1", "true", "True", "yes")
    sample_row = {
        "subject": "Physics",
        "question_text": r"What is \(E=mc^2\)?",
        "question_image": "",
        "option_a": "Energy equivalence",
        "option_a_image": "",
        "option_b": "Mass",
        "option_b_image": "",
        "option_c": "Speed of light",
        "option_c_image": "c.png",
        "option_d": "All of these",
        "option_d_image": "",
        "correct_option": "D",
    }

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    if include_sample:
        writer.writerow(sample_row)

    csv_bytes = buf.getvalue().encode("utf-8")
    resp = make_response(csv_bytes)
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    filename = "questions_template.csv" if not include_sample else "questions_template_with_sample.csv"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp