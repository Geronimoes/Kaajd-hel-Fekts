from app import create_app
import sys


print(
    "[deprecated] wa-flask.py is kept for compatibility. "
    "Preferred production entrypoint is gunicorn wsgi:app.",
    file=sys.stderr,
)

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
