from flask import Blueprint, render_template, request

student_bp = Blueprint("student", __name__)

@student_bp.route("/", methods=["GET"])
def home():
    return render_template("student/start_test.html")

@student_bp.route("/test/<int:test_id>", methods=["GET"])
def test_page(test_id):
    # placeholder values
    q = int(request.args.get("q", 1))
    total = 5
    mode = "display"
    return render_template("student/test_question.html", test_id=test_id, q=q, total=total, mode=mode)
