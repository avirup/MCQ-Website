#!/usr/bin/env bash
set -euo pipefail

PY=${PY:-python3}
APP=${APP:-manage.py}

echo "== MCQ Platform Bootstrap (bash) =="
if [ ! -d venv ]; then
  echo "Creating venv..."
  $PY -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

export FLASK_APP="$APP"
if [ ! -d migrations ]; then
  flask db init || true
fi
flask db migrate -m "auto" || true
flask db upgrade

echo "Starting Flask dev server at http://127.0.0.1:5000 ..."
flask run
