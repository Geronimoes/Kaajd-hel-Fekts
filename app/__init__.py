def create_app():
    from flask import Flask

    from .routes import main_bp

    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object("config.Config")
    app.config["UPLOAD_DIR"].mkdir(parents=True, exist_ok=True)

    if app.config.get("AUTH_ENABLED") and (
        not app.config.get("BASIC_AUTH_USERNAME")
        or not app.config.get("BASIC_AUTH_PASSWORD")
    ):
        raise RuntimeError(
            "Authentication is enabled but KAAJD_BASIC_AUTH_USERNAME or KAAJD_BASIC_AUTH_PASSWORD is missing."
        )

    app.register_blueprint(main_bp)
    return app
