# models.py
from datetime import datetime
import enum
from sqlalchemy import Index, UniqueConstraint, CheckConstraint, text, func
from extensions import db


# ---------- Enums ----------

class DifficultyEnum(enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"
    unrated = "unrated"


class ModeEnum(enum.Enum):
    display = "display"
    interactive = "interactive"


class TimerModeEnum(enum.Enum):
    per_question = "per-question"
    total_test = "total-test"


class TestStatusEnum(enum.Enum):
    active = "active"
    completed = "completed"
    discarded = "discarded"


# ---------- Models ----------

class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    questions = db.relationship(
        "Question",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Subject id={self.id} name='{self.name}'>"


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core content (LaTeX-friendly TEXT). BRD cap = 2000 chars.
    question_text = db.Column(db.Text, nullable=False)
    question_image = db.Column(db.String(255), nullable=True)

    option_a = db.Column(db.Text, nullable=False)
    option_a_image = db.Column(db.String(255), nullable=True)

    option_b = db.Column(db.Text, nullable=False)
    option_b_image = db.Column(db.String(255), nullable=True)

    option_c = db.Column(db.Text, nullable=False)
    option_c_image = db.Column(db.String(255), nullable=True)

    option_d = db.Column(db.Text, nullable=False)
    option_d_image = db.Column(db.String(255), nullable=True)

    correct_option = db.Column(db.CHAR(1), nullable=False)  # 'A' | 'B' | 'C' | 'D'

    # Stats + difficulty
    correct_count = db.Column(db.Integer, nullable=False, server_default=text("0"))
    total_attempts = db.Column(db.Integer, nullable=False, server_default=text("0"))
    difficulty = db.Column(
        db.Enum(DifficultyEnum, native_enum=False, length=10),
        nullable=False,
        server_default=text("'unrated'"),
        index=True,
    )
    last_difficulty_update = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(
        db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    subject = db.relationship("Subject", back_populates="questions")

    test_questions = db.relationship(
        "TestQuestion", back_populates="question", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Ensure correct_option is only A/B/C/D
        CheckConstraint(
            "correct_option in ('A','B','C','D')",
            name="ck_questions_correct_option_abcd",
        ),
        # Enforce BRD max length 2000 (CHAR_LENGTH works in MySQL/MariaDB)
        CheckConstraint(
            "CHAR_LENGTH(question_text) <= 2000",
            name="ck_questions_question_text_len_le_2000",
        ),
        Index("ix_questions_subject_difficulty", "subject_id", "difficulty"),
        Index("ix_questions_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Question id={self.id} subject_id={self.subject_id} diff={self.difficulty.value}>"


class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)

    # Unique public/review ID (interactive only; can be null for display)
    test_uid = db.Column(db.String(36), unique=True, nullable=True, index=True)

    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )

    difficulty_filter = db.Column(
        db.Enum(
            "easy", "medium", "hard", "mixed", "all", native_enum=False, length=10
        ),
        nullable=False,
        server_default=text("'all'"),
    )

    mode = db.Column(
        db.Enum(ModeEnum, native_enum=False, length=12),
        nullable=False,
        server_default=text("'display'"),
        index=True,
    )

    total_questions = db.Column(db.Integer, nullable=False)

    timer_mode = db.Column(
        db.Enum(TimerModeEnum, native_enum=False, length=12),
        nullable=False,
        server_default=text("'per-question'"),
    )

    per_question_duration = db.Column(db.Integer, nullable=True)  # seconds
    total_test_duration = db.Column(db.Integer, nullable=True)  # seconds
    auto_advance = db.Column(db.Boolean, nullable=False, server_default=text("0"))

    status = db.Column(
        db.Enum(TestStatusEnum, native_enum=False, length=12),
        nullable=False,
        server_default=text("'active'"),
        index=True,
    )

    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    # optional: track timing server-side (useful for anti-tamper)
    expected_end_time = db.Column(db.DateTime, nullable=True)  # for total-test timer

    subject = db.relationship("Subject")
    questions = db.relationship(
        "TestQuestion",
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="TestQuestion.sequence",
    )
    responses = db.relationship(
        "TestResponse", back_populates="test", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "total_questions > 0",
            name="ck_tests_total_questions_gt_0",
        ),
        Index("ix_tests_subject_mode_status", "subject_id", "mode", "status"),
        Index("ix_tests_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Test id={self.id} mode={self.mode.value} status={self.status.value}>"


class TestQuestion(db.Model):
    __tablename__ = "test_questions"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(
        db.Integer, db.ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence = db.Column(db.Integer, nullable=False)  # 1..N

    test = db.relationship("Test", back_populates="questions")
    question = db.relationship("Question", back_populates="test_questions")

    __table_args__ = (
        # No duplicates within a test
        UniqueConstraint(
            "test_id", "question_id", name="uq_test_questions_test_q"
        ),
        # One row per sequence in a test
        UniqueConstraint(
            "test_id", "sequence", name="uq_test_questions_test_seq"
        ),
        CheckConstraint("sequence > 0", name="ck_test_questions_sequence_gt_0"),
    )

    def __repr__(self):
        return f"<TestQuestion test_id={self.test_id} qid={self.question_id} seq={self.sequence}>"


class TestResponse(db.Model):
    __tablename__ = "test_responses"

    id = db.Column(db.Integer, primary_key=True)

    test_id = db.Column(
        db.Integer, db.ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )

    selected_option = db.Column(db.CHAR(1), nullable=False)  # 'A'|'B'|'C'|'D'
    correct_option = db.Column(db.CHAR(1), nullable=False)   # denormalized for fast review
    is_correct = db.Column(db.Boolean, nullable=False, server_default=text("0"))

    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(
        db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    test = db.relationship("Test", back_populates="responses")
    question = db.relationship("Question")

    __table_args__ = (
        CheckConstraint(
            "selected_option in ('A','B','C','D')",
            name="ck_test_responses_selected_abcd",
        ),
        CheckConstraint(
            "correct_option in ('A','B','C','D')",
            name="ck_test_responses_correct_abcd",
        ),
        UniqueConstraint(
            "test_id", "question_id", name="uq_test_responses_test_question"
        ),
        Index("ix_test_responses_test_correct", "test_id", "is_correct"),
    )

    def __repr__(self):
        return f"<TestResponse test_id={self.test_id} qid={self.question_id} correct={self.is_correct}>"

