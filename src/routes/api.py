# routes/api.py
from __future__ import annotations
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone

from extensions import db
from models import (
    Test, TestQuestion, TestResponse, Question,
    ModeEnum, TimerModeEnum, TestStatusEnum
)

api_bp = Blueprint("api", __name__)

@api_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    return {"status": "ok"}

@api_bp.route("/test/<int:test_id>/submit", methods=["POST"])
def submit_answer(test_id: int):
    """
    Save/Update the selected option for a question in an interactive test.
    Expects JSON:
    {
      "question_id": <int>,
      "selected_option": "A"|"B"|"C"|"D",
      "current_question_seq": <int>  (optional but recommended)
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400

    question_id = payload.get("question_id")
    selected_option = (payload.get("selected_option") or "").upper()
    current_seq = payload.get("current_question_seq")

    if not isinstance(question_id, int):
        return jsonify({"ok": False, "error": "question_id required"}), 400
    if selected_option not in {"A", "B", "C", "D"}:
        return jsonify({"ok": False, "error": "selected_option must be A/B/C/D"}), 400

    # Load test and basic checks
    test: Test | None = Test.query.get(test_id)
    if not test:
        return jsonify({"ok": False, "error": "Test not found"}), 404

    if test.status != TestStatusEnum.active:
        return jsonify({"ok": False, "error": "Test is not active"}), 403

    if test.mode != ModeEnum.interactive:
        return jsonify({"ok": False, "error": "Submissions are only allowed in interactive mode"}), 400

    # Server-side timing enforcement for total-test timer
    # (Per-question timer is enforced client-side; you can extend server logic later if needed.)
    if test.timer_mode == TimerModeEnum.total_test and test.expected_end_time:
        now = datetime.now(timezone.utc)
        # expected_end_time may be naive (DB default NOW()); treat as UTC if naive
        exp = test.expected_end_time
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now >= exp:
            return jsonify({"ok": False, "error": "Time expired"}), 403

    # Ensure the question belongs to this test; optionally verify the sequence, if provided
    tq: TestQuestion | None = (
        TestQuestion.query
        .filter_by(test_id=test.id, question_id=question_id)
        .first()
    )
    if not tq:
        return jsonify({"ok": False, "error": "Question not in this test"}), 400

    if isinstance(current_seq, int) and current_seq != tq.sequence:
        # Not fatal, but useful to prevent out-of-order submits if you want to be strict:
        # return jsonify({"ok": False, "error": "Sequence mismatch"}), 400
        pass

    # Load the canonical correct option
    q: Question | None = Question.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "error": "Question not found"}), 404

    is_correct = (selected_option == q.correct_option)

    # Upsert TestResponse
    resp: TestResponse | None = (
        TestResponse.query
        .filter_by(test_id=test.id, question_id=question_id)
        .first()
    )

    if resp:
        resp.selected_option = selected_option
        resp.correct_option = q.correct_option
        resp.is_correct = is_correct
    else:
        resp = TestResponse(
            test_id=test.id,
            question_id=question_id,
            selected_option=selected_option,
            correct_option=q.correct_option,
            is_correct=is_correct,
        )
        db.session.add(resp)

    db.session.commit()

    return jsonify({
        "ok": True,
        "is_correct": is_correct,
        "question_seq": tq.sequence,
    }), 200
