# Logic for test creation, randomization
# services/test_service.py
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import func
from extensions import db
from models import (
    Test, TestQuestion, TestResponse, Question,
    ModeEnum, TimerModeEnum, TestStatusEnum
)

def compute_and_finalize_test(test_id: int) -> dict:
    """
    Compute score, update per-question stats, mark test completed.
    Returns { total: int, correct: int, incorrect: int, unanswered: int }
    Idempotent: safe to call multiple times.
    """
    test = Test.query.get_or_404(test_id)

    if test.status == TestStatusEnum.completed:
        # already finalized → recompute summary from current responses
        return _summary_for(test)

    # Server-side timing guard (for total-test mode)
    if test.timer_mode == TimerModeEnum.total_test and test.expected_end_time:
        exp = test.expected_end_time
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < exp:
            # finishing early is fine; no block
            pass

    # Build lookups
    tqs = (
        TestQuestion.query
        .filter_by(test_id=test.id)
        .order_by(TestQuestion.sequence.asc())
        .all()
    )
    qids = [tq.question_id for tq in tqs]

    # Responses by question_id
    resps = (
        TestResponse.query
        .filter(TestResponse.test_id == test.id, TestResponse.question_id.in_(qids))
        .all()
    )
    resp_map = {r.question_id: r for r in resps}

    # Update stats on each answered question
    for qid in qids:
        q = Question.query.get(qid)
        if not q:
            continue
        # Total attempts increments if there's a response
        if qid in resp_map:
            q.total_attempts = (q.total_attempts or 0) + 1
            if resp_map[qid].is_correct:
                q.correct_count = (q.correct_count or 0) + 1

    # Mark test completed
    test.status = TestStatusEnum.completed
    db.session.commit()

    return _summary_for(test)

def _summary_for(test: Test) -> dict:
    total = test.total_questions
    answered = (
        TestResponse.query
        .filter_by(test_id=test.id)
        .count()
    )
    correct = (
        TestResponse.query
        .filter_by(test_id=test.id, is_correct=True)
        .count()
    )
    return {
        "total": total,
        "correct": correct,
        "incorrect": answered - correct,
        "unanswered": total - answered,
    }

def get_summary(test_id: int) -> dict:
    """
    Convenience wrapper: return summary dict for a test.
    { total, correct, incorrect, unanswered }
    """
    from models import Test  # local import to avoid circulars
    test = Test.query.get_or_404(test_id)

    total = test.total_questions
    answered = (
        TestResponse.query
        .filter_by(test_id=test.id)
        .count()
    )
    correct = (
        TestResponse.query
        .filter_by(test_id=test.id, is_correct=True)
        .count()
    )
    return {
        "total": total,
        "correct": correct,
        "incorrect": answered - correct,
        "unanswered": total - answered,
    }
