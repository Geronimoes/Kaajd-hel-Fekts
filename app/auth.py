import hmac

from flask import current_app
from flask_httpauth import HTTPBasicAuth


auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username: str, password: str) -> str | None:
    if not current_app.config.get("AUTH_ENABLED", False):
        return "anonymous"

    expected_user = current_app.config.get("BASIC_AUTH_USERNAME", "")
    expected_pass = current_app.config.get("BASIC_AUTH_PASSWORD", "")

    if not expected_user or not expected_pass:
        return None

    user_ok = hmac.compare_digest(username or "", expected_user)
    pass_ok = hmac.compare_digest(password or "", expected_pass)
    if user_ok and pass_ok:
        return username
    return None
