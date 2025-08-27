# routes/student.py
from __future__ import annotations
import uuid
from datetime import datetime, timedelta
import random

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from sqlalchemy import func
from services.test_service import compute_and_finalize_test, get_summary

from extensions import db
from models import (
    Subject, Question, Test, TestQuestion, TestResponse,
    ModeEnum, TimerModeEnum, TestStatusEnum
)


# routes/student.py (top of file, near imports)
MODE_MAP = {
    "display": ModeEnum.display,
    "interactive": ModeEnum.interactive,
}
TIMER_MAP = {
    "per-question": TimerModeEnum.per_question,
    "total-test":   TimerModeEnum.total_test,
}


student_bp = Blueprint("student", __name__)

# -----------------------
# WTForms: Start Test
# -----------------------

class StartTestForm(FlaskForm):
    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    # Modes
    mode = SelectField("Mode", choices=[
        ("display", "Display Only"),
        ("interactive", "Interactive (answer & score)"),
    ], validators=[DataRequired()])

    # Difficulty filter (optional; align with your BRD)
    difficulty_filter = SelectField("Difficulty", choices=[
        ("all", "All"),
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
        ("mixed", "Mixed"),  # mixed = balanced selection if you implement later
    ], default="all")

    number_of_questions = IntegerField("Number of Questions",
        validators=[DataRequired(), NumberRange(min=1, max=500)]
    )

    timer_mode = SelectField("Timer Mode", choices=[
        ("per-question", "Per Question"),
        ("total-test", "Total Test"),
    ], default="per-question", validators=[DataRequired()])

    per_question_duration = IntegerField("Seconds per Question",
        validators=[NumberRange(min=5, max=3600)],
        default=60
    )
    total_test_duration = IntegerField("Total Test Seconds",
        validators=[NumberRange(min=30, max=14400)],
        default=600
    )

    auto_advance = BooleanField("Auto-advance on per-question timer expiry", default=False)

    submit = SubmitField("Start Test")

# -----------------------
# Helpers
# -----------------------

def _filter_questions_query(subject_id: int, difficulty: str):
    q = Question.query.filter(Question.subject_id == subject_id)
    if difficulty in ("easy", "medium", "hard"):
        q = q.filter(Question.difficulty == difficulty)
    # "mixed" is handled at selection time if you implement balancing; here it behaves like "all"
    return q

def _count_available(subject_id: int, difficulty: str) -> int:
    return _filter_questions_query(subject_id, difficulty).count()

def _select_random_question_ids(subject_id: int, difficulty: str, n: int):
    """
    Select N distinct question IDs randomly for the given subject (+ optional difficulty).
    Efficient path: fetch IDs then python random.sample.
    """
    ids = [row.id for row in _filter_questions_query(subject_id, difficulty).with_entities(Question.id).all()]
    if len(ids) < n:
        return []
    return random.sample(ids, n)

# -----------------------
# Routes
# -----------------------

@student_bp.route("/", methods=["GET"])
def home():
    form = StartTestForm()
    form.subject_id.choices = [(s.id, s.name) for s in Subject.query.order_by(Subject.name.asc()).all()]
    return render_template("student/start_test.html", form=form)

@student_bp.route("/start-test", methods=["POST"])
def start_test():
    form = StartTestForm()
    form.subject_id.choices = [(s.id, s.name) for s in Subject.query.order_by(Subject.name.asc()).all()]

    if not form.validate_on_submit():
        flash("Please fix the errors in the form.", "error")
        return render_template("student/start_test.html", form=form), 400

    subject_id = form.subject_id.data
    mode_str = form.mode.data
    difficulty = form.difficulty_filter.data
    requested_n = form.number_of_questions.data
    timer_mode_str = form.timer_mode.data
    per_q_secs = form.per_question_duration.data
    total_secs = form.total_test_duration.data
    auto_adv = bool(form.auto_advance.data)

    # Validation based on timer mode
    if timer_mode_str == "per-question":
        if not per_q_secs or per_q_secs < 5:
            flash("Per-question duration must be at least 5 seconds.", "error")
            return render_template("student/start_test.html", form=form), 400
    else:
        if not total_secs or total_secs < 30:
            flash("Total test duration must be at least 30 seconds.", "error")
            return render_template("student/start_test.html", form=form), 400

    # Check availability
    available = _count_available(subject_id, difficulty)
    if requested_n > available:
        flash(f"Requested {requested_n} questions but only {available} available for this subject/difficulty.", "error")
        return render_template("student/start_test.html", form=form), 400

    # Pick random distinct questions
    qids = _select_random_question_ids(subject_id, difficulty, requested_n)
    if not qids:
        flash("Unable to select questions. Please try a smaller number or different filter.", "error")
        return render_template("student/start_test.html", form=form), 400

    # Build Test row
    mode = MODE_MAP[mode_str]
    timer_mode = TIMER_MAP[timer_mode_str]
    test_uid = uuid.uuid4().hex if mode == ModeEnum.interactive else None

    test = Test(
    test_uid = (uuid.uuid4().hex if mode == ModeEnum.interactive else None),
    subject_id = subject_id,
    difficulty_filter = difficulty,
    mode = mode,
    total_questions = requested_n,
    timer_mode = timer_mode,
    per_question_duration = per_q_secs if timer_mode == TimerModeEnum.per_question else None,
    total_test_duration   = total_secs if timer_mode == TimerModeEnum.total_test else None,
    auto_advance = auto_adv,
    expected_end_time = (
        datetime.utcnow() + timedelta(seconds=total_secs)
        if timer_mode == TimerModeEnum.total_test else None
        ),
    )
    db.session.add(test)
    db.session.flush()  # to get test.id

    # Insert TestQuestion sequence 1..N
    seq = 1
    for qid in qids:
        db.session.add(TestQuestion(test_id=test.id, question_id=qid, sequence=seq)) 
        seq += 1

    db.session.commit()

    # Redirect to question 1
    return redirect(url_for("student.test_page", test_id=test.id, q=1))

def _load_nth_test_question(test_id: int, n: int):
    """Return (test, test_question, question) or (None, None, None) if not found."""
    test = Test.query.get_or_404(test_id)
    if test.status != TestStatusEnum.active:
        # You can decide to redirect to review or forbid
        return test, None, None

    # bounds check
    if n < 1 or n > test.total_questions:
        return test, None, None

    tq = (
        TestQuestion.query
        .filter_by(test_id=test.id, sequence=n)
        .first()
    )
    if not tq:
        return test, None, None

    q = Question.query.get(tq.question_id)
    return test, tq, q


@student_bp.route("/test/<int:test_id>", methods=["GET"])
def test_page(test_id):
    """Render the nth question (one-by-one runner)."""
    n = request.args.get("q", type=int, default=1)

    test, tq, q = _load_nth_test_question(test_id, n)
    if q is None:
        # Out of range or not active → redirect to end/summary (you can adjust)
        if test and test.status != TestStatusEnum.active:
            flash("Test is not active.", "error")
        else:
            flash("Invalid question number.", "error")
        # For now, go back to first question or to summary hook
        return redirect(url_for("student.test_page", test_id=test_id, q=1))

    # Pre-fill selection for interactive mode (if any)
    selected_option = None
    if test.mode == ModeEnum.interactive:
        resp = (
            TestResponse.query
            .filter_by(test_id=test.id, question_id=q.id)
            .first()
        )
        if resp:
            selected_option = resp.selected_option

    # Timer config payload for client JS
    timer_config = {
        "mode": test.mode.value,  # 'display' or 'interactive'
        "auto_advance": bool(test.auto_advance),
        "timer_mode": test.timer_mode.value,  # 'per-question' or 'total-test'
        "per_question_duration": test.per_question_duration or 0,
        "total_duration": test.total_test_duration or 0,
        # Use UTC ISO format; your timer.js can compare with server time or display
        "test_end_time": test.expected_end_time.isoformat() if test.expected_end_time else None,
        "question_index": n,
        "total_questions": test.total_questions,
        "next_url": url_for("student.test_page", test_id=test.id, q=n+1) if n < test.total_questions else None,
        "finish_url": url_for("student.finish_test", test_id=test.id),  # you will implement this route
        "submit_api": url_for("api.submit_answer", test_id=test.id) if test.mode == ModeEnum.interactive else None,  # you will implement this API
    }

    # Navigation helpers
    has_prev = n > 1
    has_next = n < test.total_questions
    prev_url = url_for("student.test_page", test_id=test.id, q=n-1) if has_prev else None
    next_url = url_for("student.test_page", test_id=test.id, q=n+1) if has_next else None

    return render_template(
        "student/test_question.html",
        test=test,
        tq=tq,
        q=q,
        n=n,
        has_prev=has_prev,
        has_next=has_next,
        prev_url=prev_url,
        next_url=next_url,
        selected_option=selected_option,
        timer_config=timer_config,
    )


@student_bp.route("/finish-test/<int:test_id>", methods=["POST", "GET"])
def finish_test(test_id):
    # Finalize and redirect to review start
    summary = compute_and_finalize_test(test_id)
    return redirect(url_for("student.summary", test_id=test_id))

def _load_review_n(test_id: int, n: int):
    test = Test.query.get_or_404(test_id)
    tqs = (
        TestQuestion.query
        .filter_by(test_id=test.id)
        .order_by(TestQuestion.sequence.asc())
        .all()
    )
    if n < 1 or n > len(tqs):
        return test, None, None, None
    tq = tqs[n-1]
    q = Question.query.get_or_404(tq.question_id)
    resp = (
        TestResponse.query
        .filter_by(test_id=test.id, question_id=q.id)
        .first()
    )
    return test, tq, q, resp

# Review by internal test_id (after completion)
@student_bp.route("/review/<int:test_id>", methods=["GET"])
def review(test_id):
    n = request.args.get("q", type=int, default=1)
    test, tq, q, resp = _load_review_n(test_id, n)
    if test.status != TestStatusEnum.completed:
        flash("Test not completed yet.", "error")
        return redirect(url_for("student.test_page", test_id=test_id, q=1))
    if not q:
        # out of range: go to first
        return redirect(url_for("student.review", test_id=test_id, q=1))

    # Display rules:
    # - display mode: show correct answers only
    # - interactive: show selected vs correct
    has_prev = n > 1
    has_next = n < test.total_questions
    prev_url = url_for("student.review", test_id=test.id, q=n-1) if has_prev else None
    next_url = url_for("student.review", test_id=test.id, q=n+1) if has_next else None

    totals = get_summary(test.id)
    return render_template(
        "student/review_question.html",
        test=test, tq=tq, q=q, resp=resp,
        n=n, has_prev=has_prev, has_next=has_next,
        prev_url=prev_url, next_url=next_url,
        totals=totals
    )

# Public review by UID (interactive only, read-only)
@student_bp.route("/review-by-uid/<string:test_uid>", methods=["GET"])
def review_by_uid(test_uid):
    test = Test.query.filter_by(test_uid=test_uid).first_or_404()
    if test.mode != ModeEnum.interactive:
        abort(404)
    if test.status != TestStatusEnum.completed:
        flash("This test is not yet available for review.", "error")
        return redirect(url_for("student.test_page", test_id=test.id, q=1))

    n = request.args.get("q", type=int, default=1)
    # reuse loader
    test, tq, q, resp = _load_review_n(test.id, n)
    if not q:
        return redirect(url_for("student.review_by_uid", test_uid=test_uid, q=1))

    has_prev = n > 1
    has_next = n < test.total_questions
    prev_url = url_for("student.review_by_uid", test_uid=test_uid, q=n-1) if has_prev else None
    next_url = url_for("student.review_by_uid", test_uid=test_uid, q=n+1) if has_next else None

    totals = get_summary(test.id)
    return render_template(
        "student/review_question.html",
        test=test, tq=tq, q=q, resp=resp,
        n=n, has_prev=has_prev, has_next=has_next,
        prev_url=prev_url, next_url=next_url,
        totals=totals
    )

@student_bp.route("/summary/<int:test_id>", methods=["GET"])
def summary(test_id):
    test = Test.query.get_or_404(test_id)
    if test.status != TestStatusEnum.completed:
        return redirect(url_for("student.test_page", test_id=test.id, q=1))
    # build summary
    # If you added get_summary():
    totals = get_summary(test.id)
    # else, compute here (correct/incorrect/unanswered)
    return render_template("student/review_summary.html", test=test, totals=totals)

# Optional public summary for interactive tests by UID
@student_bp.route("/summary-by-uid/<string:test_uid>", methods=["GET"])
def summary_by_uid(test_uid):
    test = Test.query.filter_by(test_uid=test_uid).first_or_404()
    if test.mode != ModeEnum.interactive:
        abort(404)
    if test.status != TestStatusEnum.completed:
        return redirect(url_for("student.test_page", test_id=test.id, q=1))
    totals = get_summary(test.id)
    return render_template("student/review_summary.html", test=test, totals=totals, public_uid_view=True)