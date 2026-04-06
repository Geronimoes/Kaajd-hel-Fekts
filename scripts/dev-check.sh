#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
CHAT_FILE="${ROOT_DIR}/data/chat.txt"
API_BASE="http://127.0.0.1:5000"
TMP_DIR=""

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing virtualenv Python at ${PYTHON_BIN}. Create it with: python3 -m venv .venv"
  exit 1
fi

if [[ ! -f "${CHAT_FILE}" ]]; then
  echo "Missing chat file at ${CHAT_FILE}."
  exit 1
fi

echo "[1/5] Parser smoke test"
"${PYTHON_BIN}" "${ROOT_DIR}/parser_smoke_test.py"

echo "[2/5] Full CLI analysis"
"${PYTHON_BIN}" "${ROOT_DIR}/cli.py" "${CHAT_FILE}"

echo "[3/5] Cache reuse check"
"${PYTHON_BIN}" - <<'PY'
from app.analyzer import analyze_chat

r1 = analyze_chat("data/chat.txt", db_path="kaajd.sqlite3")
r2 = analyze_chat("data/chat.txt", db_path="kaajd.sqlite3")

if r1["chat_id"] != r2["chat_id"]:
    raise SystemExit("Cache check failed: chat_id mismatch")
if not r2.get("loaded_from_cache"):
    raise SystemExit("Cache check failed: second run not loaded from cache")

print("cache_ok", r1["chat_id"], r2["loaded_from_cache"])
PY

echo "[4/5] API endpoint checks"
"${PYTHON_BIN}" "${ROOT_DIR}/wa-flask.py" > /tmp/kaajd-flask.log 2>&1 &
FLASK_PID=$!

cleanup() {
  if kill -0 "${FLASK_PID}" 2>/dev/null; then
    kill "${FLASK_PID}" || true
    wait "${FLASK_PID}" 2>/dev/null || true
  fi
  if [[ -n "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

sleep 2
CONTEXT_JSON="$(curl -fsS "${API_BASE}/api/chat/1/context")"
MESSAGES_JSON="$(curl -fsS "${API_BASE}/api/chat/1/messages?limit=3")"
RESPONSE_JSON="$(curl -fsS "${API_BASE}/api/chat/1/response-patterns")"
MEDIA_JSON="$(curl -fsS "${API_BASE}/api/chat/1/media-links")"
TOPICS_JSON="$(curl -fsS "${API_BASE}/api/chat/1/topics?max_topics=4")"
RELATIONSHIPS_JSON="$(curl -fsS "${API_BASE}/api/chat/1/relationships")"
DASHBOARD_JSON="$(curl -fsS "${API_BASE}/api/chat/1/dashboard-data")"

TMP_DIR="$(mktemp -d)"

printf '%s' "${DASHBOARD_JSON}" > "${TMP_DIR}/dashboard.json"

export CONTEXT_JSON
export MESSAGES_JSON
export RESPONSE_JSON
export MEDIA_JSON
export TOPICS_JSON
export RELATIONSHIPS_JSON
export DASHBOARD_JSON_FILE="${TMP_DIR}/dashboard.json"
"${PYTHON_BIN}" - <<'PY'
import json
import os

context = json.loads(os.environ["CONTEXT_JSON"])
messages = json.loads(os.environ["MESSAGES_JSON"])
response_patterns = json.loads(os.environ["RESPONSE_JSON"])
media_links = json.loads(os.environ["MEDIA_JSON"])
topics = json.loads(os.environ["TOPICS_JSON"])
relationships = json.loads(os.environ["RELATIONSHIPS_JSON"])
with open(os.environ["DASHBOARD_JSON_FILE"], "r", encoding="utf-8") as handle:
    dashboard = json.load(handle)

if "chat" not in context or "totals" not in context:
    raise SystemExit("Context API check failed")
if "messages" not in messages or not isinstance(messages["messages"], list):
    raise SystemExit("Messages API check failed")
if "response_pairs" not in response_patterns or "reply_matrix" not in response_patterns:
    raise SystemExit("Response patterns API check failed")
if "per_person" not in media_links or "top_domains" not in media_links:
    raise SystemExit("Media links API check failed")
if "topics" not in topics or "monthly_trends" not in topics or "meta" not in topics:
    raise SystemExit("Topics API check failed")
if "affinity_scores" not in relationships or "activity_correlations" not in relationships:
    raise SystemExit("Relationships API check failed")
if "analysis" not in dashboard or "plotly" not in dashboard:
    raise SystemExit("Dashboard API check failed")
if "response_patterns" not in dashboard["plotly"]:
    raise SystemExit("Dashboard plotly payload check failed")

print(
    "api_ok",
    context["chat"]["id"],
    len(messages["messages"]),
    len(response_patterns["response_pairs"]),
    len(media_links["top_domains"]),
    len(topics["topics"]),
    len(relationships["affinity_scores"]),
    len(dashboard["plotly"].keys()),
)
PY

echo "[5/5] Done"
echo "All checks passed."
