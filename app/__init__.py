import os
from flask import Flask
from .db import init_db, close_db

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-cambia-esta-clave-antes-de-publicar"
    )
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL", "").strip()
    app.config["DATABASE_PATH"] = os.environ.get(
        "DATABASE_PATH", os.path.join(app.instance_path, "eco_reto.db")
    )

    os.makedirs(app.instance_path, exist_ok=True)

    from .routes import bp
    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    return app
